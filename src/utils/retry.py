# src/utils/retry.py
import asyncio
from functools import wraps
from typing import Callable, TypeVar, Any
import logging

T = TypeVar('T')

def async_retry(max_attempts: int = 3, backoff: float = 2.0, max_wait: float = 60.0,
                exceptions: tuple = (Exception,), logger: logging.Logger = None):
    """
    异步重试装饰器
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                attempt += 1
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_attempts:
                        raise
                    wait = min(backoff ** (attempt - 1), max_wait)
                    if logger:
                        logger.warning(f"重试 {func.__name__} ({attempt}/{max_attempts}) 等待 {wait:.2f}s: {e}")
                    await asyncio.sleep(wait)
        return wrapper
    return decorator
