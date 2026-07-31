import asyncio
from datetime import datetime
from typing import List, Dict
from src.logger import logger
from src.database import get_db_cache, channel_key
from src.candidate.models import ObservationResult, CandidateStatus
from src.config_loader import config

class CandidateObserver:
    MIN_SUCCESS_COUNT = config.candidate_min_success
    MIN_SUCCESS_RATE = config.candidate_min_success_rate
    MAX_AVG_LATENCY = config.candidate_max_latency
    MAX_OBSERVE_PER_RUN = 3000

    def __init__(self):
        self.db = None

    async def _ensure_db(self):
        if self.db is None:
            self.db = await get_db_cache()

    async def add_candidate(self, source_key: str, channel_name: str, url: str):
        await self._ensure_db()
        await self.db.add_to_candidate(source_key, channel_name, url)

    async def add_candidates_batch(self, sources: List[tuple]):
        await self._ensure_db()
        for key, name, url in sources:
            await self.db.add_to_candidate(key, name, url)

    async def observe_batch_from_cache(self, batch_size: int = None) -> List[ObservationResult]:
        if batch_size is None:
            batch_size = self.MAX_OBSERVE_PER_RUN
        await self._ensure_db()
        # 获取所有观察中的候选统计
        stats = await self.db.get_candidate_stats_batch()
        # 筛选出observing状态的候选（从数据库查询，这里简化，我们直接从数据库获取所有，然后过滤）
        cursor = await self.db._conn.execute('SELECT channel_key, name, url, status FROM candidate_pool WHERE status = ?', ('observing',))
        rows = await cursor.fetchall()
        if not rows:
            return []
        # 按发现时间排序
        cursor = await self.db._conn.execute('SELECT channel_key FROM candidate_pool WHERE status = ? ORDER BY discovered_at ASC LIMIT ?', ('observing', batch_size))
        keys = [row[0] for row in await cursor.fetchall()]
        stable_results = []
        processed = 0
        for key in keys:
            stat = stats.get(key)
            if not stat:
                continue
            # 获取名称和url
            cursor = await self.db._conn.execute('SELECT name, url FROM candidate_pool WHERE channel_key = ?', (key,))
            row = await cursor.fetchone()
            if not row:
                continue
            name, url = row
            obs = ObservationResult(source_key=key, channel_name=name, url=url)
            obs.success_count = stat["success"]
            obs.fail_count = stat["fail"]
            obs.avg_latency = stat["avg"]
            obs.check_count = stat["success"] + stat["fail"]
            obs.last_check = datetime.now()
            if obs.check_count >= self.MIN_SUCCESS_COUNT and obs.success_rate >= self.MIN_SUCCESS_RATE and obs.avg_latency <= self.MAX_AVG_LATENCY:
                obs.status = CandidateStatus.STABLE
                # 更新数据库状态
                await self.db._conn.execute('UPDATE candidate_pool SET status = ? WHERE channel_key = ?', ('stable', key))
                await self.db._conn.commit()
                stable_results.append(obs)
                logger.info(f"✅ 候选源稳定: {name} (成功率 {obs.success_rate:.2%}, 延迟 {obs.avg_latency}ms)")
            processed += 1
            if processed % 100 == 0:
                logger.info(f"  📊 观察进度: {processed}/{len(keys)}，稳定 {len(stable_results)} 个")
        return stable_results

    async def get_stable_candidates(self) -> List[ObservationResult]:
        await self._ensure_db()
        cursor = await self.db._conn.execute('SELECT channel_key, name, url, avg_latency, success_count, fail_count FROM candidate_pool WHERE status = ?', ('stable',))
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            obs = ObservationResult(source_key=row[0], channel_name=row[1], url=row[2])
            obs.avg_latency = row[3]
            obs.success_count = row[4]
            obs.fail_count = row[5]
            obs.status = CandidateStatus.STABLE
            result.append(obs)
        return result

    async def mark_promoted(self, source_key: str):
        await self._ensure_db()
        await self.db._conn.execute('UPDATE candidate_pool SET status = ? WHERE channel_key = ?', ('promoted', source_key))
        await self.db._conn.commit()

    async def get_statistics(self) -> dict:
        await self._ensure_db()
        cursor = await self.db._conn.execute('SELECT status, COUNT(*) FROM candidate_pool GROUP BY status')
        rows = await cursor.fetchall()
        stats = {'total': 0, 'observing': 0, 'stable': 0, 'promoted': 0, 'rejected': 0}
        for status, count in rows:
            stats['total'] += count
            if status == 'observing': stats['observing'] = count
            elif status == 'stable': stats['stable'] = count
            elif status == 'promoted': stats['promoted'] = count
            elif status == 'rejected': stats['rejected'] = count
        return stats
