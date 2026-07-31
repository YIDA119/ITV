import re
from pathlib import Path
from typing import Dict, Optional, List, Pattern
from src.config_loader import config

class AliasMatcher:
    def __init__(self, alias_file: Path = None):
        self.alias_file = alias_file or config.alias_file
        self.exact_mappings: Dict[str, str] = {}
        self.regex_mappings: List[tuple] = []
        self._load()

    def _load(self):
        if not self.alias_file.exists():
            print(f"⚠️ 别名文件不存在: {self.alias_file}")
            return
        with open(self.alias_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split(',')] if ',' in line else line.split(':', 1)
                if len(parts) < 2:
                    print(f"⚠️ 别名文件第 {line_num} 行格式错误，跳过: {line}")
                    continue
                standard = parts[0]
                for alias in parts[1:]:
                    alias = alias.strip()
                    if not alias:
                        continue
                    if alias.startswith('re:'):
                        try:
                            pattern = re.compile(alias[3:].strip(), re.IGNORECASE)
                            self.regex_mappings.append((pattern, standard))
                        except re.error as e:
                            print(f"⚠️ 别名文件第 {line_num} 行正则错误: {e}")
                    else:
                        self.exact_mappings[alias.lower()] = standard
        print(f"✅ 已加载别名规则：精确 {len(self.exact_mappings)}，正则 {len(self.regex_mappings)}")

    def match(self, channel_name: str) -> Optional[str]:
        if not channel_name:
            return None
        name_lower = channel_name.lower()
        if name_lower in self.exact_mappings:
            return self.exact_mappings[name_lower]
        for pattern, standard in self.regex_mappings:
            if pattern.search(channel_name):
                return standard
        return None

    def normalize(self, channel_name: str) -> str:
        mapped = self.match(channel_name)
        return mapped if mapped is not None else channel_name

_matcher = None
def get_alias_matcher() -> AliasMatcher:
    global _matcher
    if _matcher is None and config.enable_alias:
        _matcher = AliasMatcher()
    return _matcher
