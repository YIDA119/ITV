# src/services/demo_service.py
"""Demo 服务 - 支持别名匹配"""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

from src.core.config import get_config
from src.core.constants import PROVINCES
from src.infrastructure.logger import get_logger
from src.filters.alias import AliasMatcher

logger = get_logger(__name__)

try:
    from pypinyin import lazy_pinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False

# 分类前缀映射
CATEGORY_PREFIXES = {
    "☘️": "地方",
    "📺": "央视",
    "📡": "卫视",
    "🌊": "港澳台",
}

# 全局别名匹配器
_alias_matcher = None


def get_alias_matcher() -> Optional[AliasMatcher]:
    """获取别名匹配器（单例）"""
    global _alias_matcher
    if _alias_matcher is None:
        _alias_matcher = AliasMatcher()
    return _alias_matcher


def load_demo_order(demo_file: Optional[Path] = None) -> List[Tuple[str, str]]:
    """加载 demo 顺序，返回 (分类, 频道名/分类模式)"""
    config = get_config()
    demo_file = demo_file or config.demo_file
    
    if not demo_file.exists():
        logger.warning(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    
    order = []
    current_category = None
    
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.endswith(",#genre#") or line.endswith(", #genre#"):
                cat_name = line.replace(",#genre#", "").replace(", #genre#", "").strip()
                current_category = cat_name
                # 分类行也添加到 order 中
                order.append((cat_name, cat_name))
                continue
            
            if line.startswith('#'):
                continue
            
            if current_category is not None:
                order.append((current_category, line))
    
    logger.info(f"📋 加载 demo 顺序: {len(order)} 个条目")
    return order


def normalize_channel_name(name: str) -> str:
    """标准化频道名（用于匹配）"""
    if not name:
        return ""
    # 转小写
    name = name.lower()
    # 移除清晰度标签
    name = re.sub(r'\s*(?:1080[pi]|720[pi]|4k|8k|hd|高清|超清|标清)\s*', '', name)
    # 移除括号内容
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    # 移除特殊字符
    name = re.sub(r'[^\w\u4e00-\u9fa5]', '', name)
    return name


def match_channel_name(channel_name: str, demo_name: str) -> bool:
    """
    匹配频道名 - 支持别名匹配
    优先级：别名匹配 > 精确匹配 > 包含匹配 > 拼音匹配
    """
    if not channel_name or not demo_name:
        return False
    
    # 1. 通过别名匹配器标准化频道名
    matcher = get_alias_matcher()
    if matcher:
        # 获取频道的标准名（别名映射后的名称）
        normalized = matcher.normalize(channel_name)
        # 如果标准化后的名称与 demo 名称匹配
        if normalized == demo_name:
            logger.debug(f"✅ 别名匹配: {channel_name} -> {normalized} == {demo_name}")
            return True
        # 检查标准化后的名称是否包含 demo 名称
        if demo_name in normalized:
            logger.debug(f"✅ 别名包含匹配: {channel_name} -> {normalized} 包含 {demo_name}")
            return True
    
    # 2. 检查是否是分类匹配模式（如 ☘️上海频道）
    if is_category_match(demo_name, channel_name):
        return True
    
    cn_lower = channel_name.lower()
    dn_lower = demo_name.lower()
    
    # 3. 央视频道数字匹配
    cctv_pattern = re.compile(r'cctv[-\s]*(\d+(?:k)?)', re.IGNORECASE)
    m1 = cctv_pattern.search(channel_name)
    m2 = cctv_pattern.search(demo_name)
    
    if m1 and m2 and m1.group(1).lower() == m2.group(1).lower():
        num = m1.group(1).lower()
        if num in ["4k", "8k"]:
            return True
        if num.isdigit():
            area_keywords = {"欧洲": ["欧洲", "europe"], "美洲": ["美洲", "america"]}
            for kw, variants in area_keywords.items():
                if kw in dn_lower:
                    if not any(v in cn_lower for v in variants):
                        return False
            return True
    
    # 4. 包含匹配
    if dn_lower in cn_lower or cn_lower in dn_lower:
        return True
    
    # 5. 拼音匹配
    if HAS_PYPINYIN:
        def to_pinyin(text):
            return ''.join(lazy_pinyin(text)).lower()
        if to_pinyin(demo_name) in to_pinyin(channel_name):
            return True
    
    # 6. 去特殊字符匹配
    if normalize_channel_name(channel_name) == normalize_channel_name(demo_name):
        return True
    
    return False


def is_category_match(demo_name: str, channel_name: str) -> bool:
    """检查是否是分类匹配（如 demo 中是 "☘️上海频道"）"""
    for prefix in CATEGORY_PREFIXES.keys():
        if demo_name.startswith(prefix):
            cat_part = demo_name[len(prefix):].replace("频道", "").strip()
            if cat_part in channel_name:
                return True
            for prov in PROVINCES:
                if prov == cat_part and prov in channel_name:
                    return True
                if len(prov) == 2 and prov in channel_name:
                    return True
    return False


def extract_province_from_name(channel_name: str) -> Optional[str]:
    """从频道名提取省份"""
    for prov in PROVINCES:
        if prov in channel_name:
            return prov
    return None


def get_channel_aliases(channel_name: str) -> List[str]:
    """
    获取频道的所有别名（用于匹配）
    返回：[原始名, 别名1, 别名2, ...]
    """
    matcher = get_alias_matcher()
    aliases = [channel_name]
    
    if matcher:
        # 获取标准名
        std_name = matcher.normalize(channel_name)
        if std_name != channel_name:
            aliases.append(std_name)
        
        # 检查是否有其他别名映射到同一个标准名
        # 遍历精确映射
        for alias, standard in matcher.exact_mappings.items():
            if standard == std_name and alias not in aliases:
                aliases.append(alias)
    
    return aliases
