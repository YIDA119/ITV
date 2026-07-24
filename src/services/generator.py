# src/services/generator.py
"""生成服务 - 支持分类匹配"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from src.core.config import get_config
from src.core.constants import PROVINCES
from src.infrastructure.logger import get_logger
from src.services.demo_service import load_demo_order, match_channel_name, is_category_match, extract_province_from_name

logger = get_logger(__name__)


class Generator:
    """输出生成器"""
    
    def __init__(self):
        self.config = get_config()
    
    def generate_all(self, channels: List[Dict], demo_order: List[Tuple[str, str]] = None) -> None:
        """生成所有输出"""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if demo_order is None:
            demo_order = load_demo_order()
        
        categorized = self._categorize_by_demo(channels, demo_order)
        
        self._generate_m3u(categorized, output_dir / "tv.m3u")
        self._generate_txt(categorized, output_dir / "tv.txt")
        self._generate_multi_m3u(categorized, output_dir / "tv_multi.m3u")
        self._generate_json(channels, output_dir / "channels.json")
        
        logger.info("✅ 所有输出文件已生成")
    
    def _categorize_by_demo(self, channels: List[Dict], demo_order: List[Tuple[str, str]]) -> Dict[str, List[Dict]]:
        """
        按 demo 顺序分类
        支持分类匹配：☘️上海频道 匹配所有上海频道
        """
        result = {}
        
        if not demo_order:
            logger.warning("⚠️ demo_order 为空")
            return result
        
        # 构建频道名到频道的映射
        channel_map = {ch["name"]: ch for ch in channels}
        
        # 按省份分组频道
        province_channels = {}
        for ch in channels:
            prov = extract_province_from_name(ch["name"])
            if prov:
                if prov not in province_channels:
                    province_channels[prov] = []
                province_channels[prov].append(ch)
        
        matched_names = set()
        total_matched = 0
        
        # 按 demo 顺序遍历
        for cat, demo_name in demo_order:
            if cat not in result:
                result[cat] = []
            
            matched_ch = None
            
            # 1. 检查是否是分类匹配（☘️上海频道）
            if is_category_match(demo_name, ""):
                # 提取省份
                for prefix in ["☘️", "📺", "📡", "🌊"]:
                    if demo_name.startswith(prefix):
                        cat_part = demo_name[len(prefix):].replace("频道", "").strip()
                        # 匹配该省份的所有频道
                        if cat_part in province_channels:
                            prov = cat_part
                            for ch in province_channels.get(prov, []):
                                if ch["name"] not in matched_names:
                                    result[cat].append(ch)
                                    matched_names.add(ch["name"])
                                    total_matched += 1
                            logger.info(f"📌 分类匹配: {demo_name} -> {len(province_channels.get(prov, []))} 个频道")
                        break
                continue
            
            # 2. 精确匹配
            if demo_name in channel_map:
                matched_ch = channel_map[demo_name]
                if matched_ch["name"] not in matched_names:
                    matched_names.add(matched_ch["name"])
                    total_matched += 1
                    result[cat].append(matched_ch)
                continue
            
            # 3. 模糊匹配
            for name, ch in channel_map.items():
                if name in matched_names:
                    continue
                if match_channel_name(name, demo_name):
                    matched_names.add(name)
                    total_matched += 1
                    result[cat].append(ch)
                    break
        
        logger.info(f"📊 Demo 匹配结果: {total_matched} 个频道")
        
        # 统计各分类数量
        for cat, ch_list in result.items():
            if ch_list:
                logger.info(f"   {cat}: {len(ch_list)} 个频道")
        
        return result
    
    def _generate_m3u(self, categorized: Dict[str, List[Dict]], path: Path) -> None:
        """生成 M3U"""
        total = sum(len(ch) for ch in categorized.values())
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Total channels: {total}\n")
            
            for cat, channels in categorized.items():
                if not channels:
                    continue
                f.write(f"\n# ----- {cat} ({len(channels)}个频道) -----\n")
                for ch in channels:
                    url = ch.get("url", "")
                    if url:
                        name = ch.get("name", "未知频道")
                        f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
        
        logger.info(f"✅ M3U 文件已生成: {path} ({total} 个频道)")
    
    def _generate_txt(self, categorized: Dict[str, List[Dict]], path: Path) -> None:
        """生成 TXT"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            
            for cat, channels in categorized.items():
                if not channels:
                    continue
                f.write(f"\n{cat},#genre#\n")
                for ch in channels:
                    url = ch.get("url", "")
                    if url:
                        name = ch.get("name", "未知频道")
                        f.write(f"{name},{url}\n")
        
        logger.info(f"✅ TXT 文件已生成: {path}")
    
    def _generate_multi_m3u(self, categorized: Dict[str, List[Dict]], path: Path) -> None:
        """生成多源 M3U"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            
            for cat, channels in categorized.items():
                if not channels:
                    continue
                f.write(f"\n# ----- {cat} ({len(channels)}个频道) -----\n")
                for ch in channels:
                    urls = ch.get("urls", [ch.get("url", "")])
                    valid_urls = [u for u in urls if u and u.startswith(('http://', 'https://'))]
                    if valid_urls:
                        name = ch.get("name", "未知频道")
                        f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{" # ".join(valid_urls)}\n')
        
        logger.info(f"✅ 多源 M3U 文件已生成: {path}")
    
    def _generate_json(self, channels: List[Dict], path: Path) -> None:
        """生成 JSON"""
        data = {
            "version": "2.0",
            "total": len(channels),
            "generated": datetime.now().isoformat(),
            "channels": []
        }
        
        for ch in channels:
            channel_info = {
                "name": ch.get("name", ""),
                "url": ch.get("url", ""),
                "urls": ch.get("urls", []),
                "latency": ch.get("latency"),
                "codec": ch.get("video_codec", ""),
                "category": ch.get("group_title", ""),
                "is_fixed": ch.get("is_fixed", False),
            }
            channel_info = {k: v for k, v in channel_info.items() if v}
            data["channels"].append(channel_info)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ JSON 文件已生成: {path}")
