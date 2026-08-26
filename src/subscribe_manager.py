# src/subscribe_manager.py
import re
from pathlib import Path
from typing import List

from src.config_loader import config
from src.logger import logger

class SubscribeManager:
    def __init__(self, subscribe_file: Path = None):
        self.subscribe_file = subscribe_file or config.subscribe_file
        self._url_pattern = re.compile(r'(https?://[^\s]+)')

    def parse(self) -> List[str]:
        """解析订阅文件，返回 URL 列表（忽略白名单）"""
        if not self.subscribe_file.exists():
            logger.debug(f"订阅文件不存在: {self.subscribe_file}")
            return []

        urls = []
        inside_whitelist = False
        with open(self.subscribe_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    inside_whitelist = line.upper() == '[WHITELIST]'
                    continue
                if inside_whitelist:
                    continue  # 白名单内的 URL 不加入普通列表，但可单独获取
                match = self._url_pattern.search(line)
                if match:
                    urls.append(match.group(0))
        return urls

    def get_whitelist(self) -> List[str]:
        if not self.subscribe_file.exists():
            return []
        urls = []
        inside_whitelist = False
        with open(self.subscribe_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    inside_whitelist = line.upper() == '[WHITELIST]'
                    continue
                if inside_whitelist:
                    match = self._url_pattern.search(line)
                    if match:
                        urls.append(match.group(0))
        return urls


def get_subscribe_urls() -> List[str]:
    """获取所有订阅源 URL（不含白名单）"""
    manager = SubscribeManager()
    return manager.parse()

def get_whitelist_urls() -> List[str]:
    manager = SubscribeManager()
    return manager.get_whitelist()
