# src/subscribe_manager.py
import re
from pathlib import Path
from typing import List, Optional

from src.config_loader import config
from src.logger import logger


class SubscribeManager:
    def __init__(self, subscribe_file: Optional[Path] = None):
        self.config = config
        self.subscribe_file = subscribe_file or self.config.subscribe_file
        self._url_pattern = re.compile(r'(https?://[^\s]+)')
        self._kv_pattern = re.compile(r'(?P<key>\w+)=(?P<value>[^\s]+)')
    
    def parse(self) -> List[str]:
        if not self.subscribe_file.exists():
            logger.debug(f"订阅文件不存在: {self.subscribe_file}")
            return []
        
        urls = []
        with open(self.subscribe_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    continue  # 跳过节标记，后面直接取所有URL
                match = self._url_pattern.search(line)
                if match:
                    urls.append(match.group(0))
        return urls
    
    def get_all_subscribe_urls(self) -> List[str]:
        return self.parse()
    
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
    return SubscribeManager().parse()


def get_whitelist_urls() -> List[str]:
    return SubscribeManager().get_whitelist()
