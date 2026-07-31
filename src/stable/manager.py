# src/stable/manager.py
from src.database import get_db_cache
from src.logger import logger

class StableManager:
    def __init__(self):
        self.db = None

    async def _ensure_db(self):
        if self.db is None:
            self.db = await get_db_cache()
        return self.db

    async def get_db(self):
        """公共方法，供外部获取数据库实例"""
        return await self._ensure_db()

    async def get_stable_sources(self) -> dict:
        await self._ensure_db()
        return await self.db.get_all_stable_sources()

    async def get_stable_source(self, channel_name: str) -> dict:
        await self._ensure_db()
        return await self.db.get_stable_source(channel_name)

    async def promote_candidate(self, channel_name: str, url: str, latency: int, video_codec: str = '') -> bool:
        await self._ensure_db()
        existing = await self.db.get_stable_source(channel_name)
        if existing and existing.get('is_fixed') and not existing.get('auto_optimize', True):
            logger.warning(f"⚠️ {channel_name} 是固定源且禁止自动优化，拒绝提升")
            return False
        await self.db.upsert_stable_source(channel_name, url, latency, video_codec, is_fixed=False, auto_optimize=True)
        logger.info(f"✅ {channel_name} 已提升为稳定源")
        return True

    async def set_fixed_source(self, channel_name: str, url: str, latency: int = 0, video_codec: str = '', auto_optimize: bool = True) -> bool:
        await self._ensure_db()
        await self.db.upsert_stable_source(channel_name, url, latency, video_codec, is_fixed=True, auto_optimize=auto_optimize)
        logger.info(f"📌 {channel_name} 已设为固定源 (auto_optimize={auto_optimize})")
        return True

    async def replace_source(self, channel_name: str, new_url: str, latency: int, video_codec: str = '') -> bool:
        await self._ensure_db()
        existing = await self.db.get_stable_source(channel_name)
        if existing and existing.get('is_fixed') and not existing.get('auto_optimize', True):
            logger.warning(f"⚠️ {channel_name} 是固定源且禁止自动优化，拒绝替换")
            return False
        is_fixed = existing.get('is_fixed', False) if existing else False
        auto_opt = existing.get('auto_optimize', True) if existing else True
        await self.db.upsert_stable_source(channel_name, new_url, latency, video_codec, is_fixed=is_fixed, auto_optimize=auto_opt)
        logger.info(f"🔄 {channel_name} 已替换为 {new_url[:50]}...")
        return True

    async def record_failure(self, channel_name: str):
        await self._ensure_db()
        src = await self.db.get_stable_source(channel_name)
        if src:
            await self.db.update_stable_status(channel_name, fail_count=src.get('fail_count',0)+1)

    async def record_success(self, channel_name: str):
        await self._ensure_db()
        src = await self.db.get_stable_source(channel_name)
        if src and src.get('fail_count',0) > 0:
            await self.db.update_stable_status(channel_name, fail_count=0)
