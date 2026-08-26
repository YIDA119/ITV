import asyncio
from datetime import datetime
from pathlib import Path
from src.logger import logger
from src.database import get_db_cache, channel_key
from src.source_pool.discoverer import SourceDiscoverer
from src.candidate.observer import CandidateObserver
from src.stable.manager import StableManager
from src.quality.monitor import QualityMonitor
from src.config_loader import config
from src.speed_tester import test_channels_concurrent

class IPTVOrchestrator:
    MAX_NEW_SOURCES_PER_RUN = 5000
    MAX_OBSERVE_PER_RUN = 3000

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = None
        self.discoverer = SourceDiscoverer(self.data_dir / "source_pool.json")
        self.candidate_observer = CandidateObserver()
        self.stable_manager = StableManager()
        self.quality_monitor = QualityMonitor(self.stable_manager)
        self.stats = {"last_discover": None, "last_observe": None, "total_promoted": 0}

    async def _ensure_db(self):
        if self.db is None:
            self.db = await get_db_cache()

    async def discover_phase(self) -> dict:
        logger.info("="*50 + "\n阶段1: 发现新源（国内频道）\n" + "="*50)
        await self._ensure_db()
        try:
            new_sources = await asyncio.wait_for(
                self.discoverer.discover(self.db, filter_domestic=True, force_refresh=True),
                timeout=120
            )
            total_new = sum(len(s) for s in new_sources.values())
            self.stats["last_discover"] = datetime.now()
            if total_new == 0:
                logger.info("✅ 没有发现新源")
                return {}
            added = []
            count = 0
            for channel_name, sources in new_sources.items():
                for src in sources:
                    if count >= self.MAX_NEW_SOURCES_PER_RUN:
                        break
                    added.append((src.get_key(), channel_name, src.url))
                    count += 1
                if count >= self.MAX_NEW_SOURCES_PER_RUN:
                    break
            await self.candidate_observer.add_candidates_batch(added)
            logger.info(f"✅ 发现阶段完成: {len(added)} 个新源进入候选池")
            return new_sources
        except Exception as e:
            logger.error(f"❌ 发现新源阶段失败: {e}")
            return {}

    async def _speed_test_phase(self):
        """测速所有观察中的候选源（阶段1.5）- 直接从数据库查询"""
        await self._ensure_db()
        # 从数据库查询 observing 状态的候选源
        rows = await self.db.fetch_all(
            "SELECT channel_key, name, url FROM candidate_pool WHERE status = 'observing'"
        )
        if not rows:
            logger.info("📭 没有候选源需要测速")
            return

        logger.info("="*50 + "\n阶段1.5: 测速候选源\n" + "="*50)
        logger.info(f"📊 候选池中有 {len(rows)} 个源需要测速")

        channels_dict = {}
        for row in rows:
            key = row['channel_key']
            channels_dict[key] = {
                "name": row['name'],
                "url": row['url'],
                "source_key": key,
            }

        logger.info(f"🔍 开始测速 {len(channels_dict)} 个候选源...")
        valid_channels = await test_channels_concurrent(channels_dict)
        logger.info(f"✅ 测速完成: {len(valid_channels)}/{len(channels_dict)} 个有效")

        # 直接提升低延迟源（每个频道取最佳）
        if valid_channels:
            valid_channels.sort(key=lambda x: x.get('latency', 9999))
            best_by_channel = {}
            for ch in valid_channels:
                name = ch['name']
                if name not in best_by_channel or ch.get('latency', 9999) < best_by_channel[name].get('latency', 9999):
                    best_by_channel[name] = ch

            top = list(best_by_channel.values())
            logger.info(f"📌 提升 {len(top)} 个频道的稳定源...")
            for ch in top[:200]:
                await self.stable_manager.promote_candidate(
                    ch['name'],
                    ch['url'],
                    ch.get('latency', 0),
                    ch.get('video_codec', '')
                )

    async def observe_phase(self) -> list:
        logger.info("="*50 + "\n阶段2: 从缓存观察候选源\n" + "="*50)
        try:
            stats = await self.candidate_observer.get_statistics()
            if stats['observing'] == 0:
                logger.info("📭 没有候选源需要观察")
                return []
            stable_candidates = await self.candidate_observer.observe_batch_from_cache(
                batch_size=self.MAX_OBSERVE_PER_RUN
            )
            self.stats["last_observe"] = datetime.now()
            logger.info(f"✅ 观察阶段完成: {len(stable_candidates)} 个源达到稳定标准")
            return stable_candidates
        except Exception as e:
            logger.error(f"❌ 观察候选源阶段失败: {e}")
            return []

    async def promote_phase(self, stable_candidates: list = None) -> int:
        logger.info("="*50 + "\n阶段3: 提升稳定源\n" + "="*50)
        try:
            if stable_candidates is None:
                stable_candidates = await self.candidate_observer.get_stable_candidates()
            if not stable_candidates:
                logger.info("📭 没有稳定的候选源需要提升")
                return 0
            promoted = 0
            for obs in stable_candidates[:50]:
                existing = await self.stable_manager.get_stable_source(obs.channel_name)
                if existing and existing.get('is_fixed') and not existing.get('auto_optimize', True):
                    continue
                if existing and existing.get('latency', 9999) < obs.avg_latency:
                    continue
                if await self.stable_manager.promote_candidate(obs.channel_name, obs.url, obs.avg_latency, ""):
                    promoted += 1
                    await self.candidate_observer.mark_promoted(obs.source_key)
                    logger.info(f"📌 已提升: {obs.channel_name}")
            self.stats["total_promoted"] += promoted
            logger.info(f"✅ 提升阶段完成: {promoted} 个源被提升")
            return promoted
        except Exception as e:
            logger.error(f"❌ 提升稳定源阶段失败: {e}")
            return 0

    async def run_once(self, skip_discover: bool = False) -> dict:
        logger.info("🚀 IPTV 自治系统启动")
        if skip_discover:
            logger.info("⏭️ 跳过发现阶段")
        else:
            await self.discover_phase()

        # === 关键：测速已有候选源（直接从数据库查询） ===
        await self._speed_test_phase()

        stable_candidates = await self.observe_phase()
        await self.promote_phase(stable_candidates)

        logger.info("📊 自治模式统计:")
        stats = await self.candidate_observer.get_statistics()
        logger.info(f"  候选池总数: {stats['total']}, 观察中: {stats['observing']}, 稳定: {stats['stable']}")
        logger.info(f"  本次新提升: {self.stats.get('total_promoted', 0)}")
        return self.stats


_orchestrator = None

async def run_autonomous_mode(skip_discover: bool = False):
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IPTVOrchestrator()
    return await _orchestrator.run_once(skip_discover=skip_discover)
