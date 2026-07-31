import asyncio
import aiohttp
from src.config_loader import config
from src.logger import logger
from src.proxy_utils import fetch_with_proxy_fallback
from src.http_client import HttpClient

class FetchError(Exception):
    pass

async def fetch_url_with_metadata(url: str, db, force_refresh: bool = False):
    if not force_refresh and db:
        cached = await db.get_raw_source(url)
        if cached:
            logger.debug(f"✅ 使用缓存: {url}")
            return cached
    logger.info(f"🔄 拉取: {url}")
    async with HttpClient.session_context() as session:
        content, _ = await fetch_with_proxy_fallback(session, url)
        if content is not None:
            if db:
                await db.set_raw_source(url, content)
            return content
        raise FetchError(f"拉取失败: {url}")

async def fetch_all_sources_incremental(sources: list, db, force_refresh: bool = False) -> dict:
    tasks = [fetch_url_with_metadata(url, db, force_refresh) for url in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    output = {}
    for url, res in zip(sources, results):
        if isinstance(res, Exception):
            logger.warning(f"⚠️ 拉取失败 {url}: {res}")
            if not force_refresh and db:
                cached = await db.get_raw_source(url)
                if cached:
                    output[url] = cached
                    logger.info(f"📦 使用旧缓存: {url}")
                else:
                    output[url] = None
            else:
                output[url] = None
        else:
            output[url] = res
    return output
