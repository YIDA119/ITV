# src/services/demo_service.py
"""Demo 服务"""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from src.core.config import get_config
from src.core.constants import PROVINCES
from src.infrastructure.logger import get_logger

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


def load_demo_order(demo_file: Optional[Path] = None) -> List[Tuple[str, str]]:
    """加载 demo 顺序，返回 (分类, 频道名/分类模式)"""
    config = get_config()
    demo_file = demo_file or config.demo_file
    
    if not demo_file.exists():
        logger.warning(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    
    order = []
    current_category = None
    is_category_line = False
    
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是分类标题行（以 ☘️📺📡🌊 开头，以 #genre# 结尾）
            if line.endswith(",#genre#") or line.endswith(", #genre#"):
                cat_name = line.replace(",#genre#", "").replace(", #genre#", "").strip()
                current_category = cat_name
                is_category_line = True
                # 分类行也添加到 order 中，用于匹配省份
                order.append((cat_name, cat_name))
                continue
            
            if line.startswith('#'):
                continue
            
            if current_category is not None:
                order.append((current_category, line))
                is_category_line = False
    
    logger.info(f"📋 加载 demo 顺序: {len(order)} 个条目")
    return order


def match_channel_name(channel_name: str, demo_name: str) -> bool:
    """匹配频道名"""
    if not demo_name:
        return False
    
    cn_lower = channel_name.lower()
    dn_lower = demo_name.lower()
    
    # 1. 检查是否是分类匹配模式（如 ☘️上海频道）
    if is_category_match(demo_name, channel_name):
        return True
    
    # 2. 央视频道数字匹配
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
    
    # 3. 包含匹配
    if dn_lower in cn_lower or cn_lower in dn_lower:
        return True
    
    # 4. 拼音匹配
    if HAS_PYPINYIN:
        def to_pinyin(text):
            return ''.join(lazy_pinyin(text)).lower()
        if to_pinyin(demo_name) in to_pinyin(channel_name):
            return True
    
    # 5. 去特殊字符匹配
    def clean(s):
        return re.sub(r'[^a-zA-Z\u4e00-\u9fa5]', '', s).lower()
    if clean(demo_name) in clean(channel_name):
        return True
    
    return False


def is_category_match(demo_name: str, channel_name: str) -> bool:
    """
    检查是否是分类匹配（如 demo 中是 "☘️上海频道"，频道是 "上海新闻综合"）
    """
    # 检查 demo_name 是否以分类前缀开头
    for prefix in CATEGORY_PREFIXES.keys():
        if demo_name.startswith(prefix):
            # 提取省份/分类名
            cat_part = demo_name[len(prefix):]
            # 去掉 "频道" 后缀
            cat_part = cat_part.replace("频道", "").strip()
            
            # 检查频道名是否包含该省份/分类
            if cat_part in channel_name:
                return True
            
            # 如果是省份，检查省份简称
            for prov in PROVINCES:
                if prov == cat_part and prov in channel_name:
                    return True
                # 检查省份简称
                if len(prov) == 2 and prov in channel_name:
                    return True
    
    return False


def extract_province_from_name(channel_name: str) -> Optional[str]:
    """从频道名提取省份"""
    for prov in PROVINCES:
        if prov in channel_name:
            return prov
    return None
