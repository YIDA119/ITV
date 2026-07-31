import aiohttp
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from src.config_loader import config

class HttpClient:
    _session: aiohttp.ClientSession = None

    @classmethod
    def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=20, ttl_dns_cache=300)
            timeout = aiohttp.ClientTimeout(total=config.http_timeout + 5)
            cls._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return cls._session

    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None

    @classmethod
    @asynccontextmanager
    async def session_context(cls) -> AsyncGenerator[aiohttp.ClientSession, None]:
        session = cls.get_session()
        try:
            yield session
        finally:
            pass
