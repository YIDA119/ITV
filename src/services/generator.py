# src/services/generator.py
"""生成服务"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from src.core.config import get_config
from src.core.constants import OUTPUT_CATEGORY_ORDER, CATEGORY_CCTV, CATEGORY_SATELLITE, CATEGORY_HKMT, CATEGORY_LOCAL
from src.infrastructure.logger import get_logger
from src.services.demo_service import load_demo_order, match_channel_name

logger = get_logger(__name__)


class Generator:
    """输出生成器"""
    
    def __init__(self):
        self.config = get_config()
    
    def generate_all(self, channels: List[Dict], demo_order: List[Tuple[str, str]] = None) -> None:
        """生成所有输出"""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 按 demo 分类
        categorized = self._categorize_by_demo(channels, demo_order)
        
        # 生成 M3U
        self._generate_m3u(categorized, output_dir / "tv.m3u")
        
        # 生成 TXT
        self._generate_txt(categorized, output_dir / "tv.txt")
        
        # 生成多源 M3U
        self._generate_multi_m3u(categorized, output_dir / "tv_multi.m3u")
        
        # 生成 JSON
        self._generate_json(channels, output_dir / "channels.json")
        
        logger.info("✅ 所有输出文件已生成")
    
    def _categorize_by_demo(self, channels: List[Dict], demo_order: List[Tuple[str, str]]) -> Dict[str, List[Dict]]:
        """按 demo 分类并保持顺序"""
        result = {}
        
        # 如果 demo_order 为空，使用默认分类
        if not demo_order:
            demo_order = load_demo_order()
        
        # 构建频道名到频道的映射（支持模糊匹配）
        channel_map = {}
        for ch in channels:
            channel_map[ch["name"]] = ch
        
        # 先按 demo 顺序匹配
        matched_names = set()
        
        for cat, demo_name in demo_order:
            if cat not in result:
                result[cat] = []
            
            # 精确匹配
            if demo_name in channel_map:
                ch = channel_map[demo_name]
                result[cat].append(ch)
                matched_names.add(demo_name)
                continue
            
            # 模糊匹配
            for name, ch in channel_map.items():
                if name in matched_names:
                    continue
                if match_channel_name(name, demo_name):
                    result[cat].append(ch)
                    matched_names.add(name)
                    break
        
        # 处理未匹配的频道 - 按分类归类
        remaining = [ch for ch in channels if ch["name"] not in matched_names]
        
        for ch in remaining:
            # 根据频道名推断分类
            cat = self._infer_category(ch["name"])
            if cat not in result:
                result[cat] = []
            result[cat].append(ch)
        
        return result
    
    def _infer_category(self, name: str) -> str:
        """推断频道分类"""
        name_lower = name.lower()
        
        # 央视
        if "cctv" in name_lower or "央视" in name or "中央电视" in name:
            return CATEGORY_CCTV
        
        # 港澳台
        hk_keywords = ["tvb", "翡翠", "明珠", "凤凰", "无线", "rthk", "hoy", "viu", 
                       "东森", "民视", "台视", "华视", "中视", "三立", "纬来", "tvbs",
                       "香港", "澳门", "台湾", "澳视"]
        for kw in hk_keywords:
            if kw in name_lower:
                return CATEGORY_HKMT
        
        # 卫视
        if "卫视" in name:
            return CATEGORY_SATELLITE
        
        # 地方
        provinces = ["北京", "上海", "广东", "浙江", "江苏", "湖南", "湖北", "山东", 
                     "河南", "四川", "福建", "安徽", "辽宁", "陕西", "河北", "江西",
                     "黑龙江", "吉林", "山西", "云南", "贵州", "甘肃", "海南", "青海",
                     "宁夏", "新疆", "西藏", "广西", "内蒙古", "重庆", "天津"]
        for prov in provinces:
            if prov in name:
                return CATEGORY_LOCAL
        
        # 智能补充分类（保留原分类）
        return "其他"
    
    def _generate_m3u(self, categorized: Dict[str, List[Dict]], path: Path) -> None:
        """生成 M3U"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            
            for cat, channels in categorized.items():
                if not channels:
                    continue
                # 分类标题
                f.write(f"\n# ----- {cat} ({len(channels)}个频道) -----\n")
                for ch in channels:
                    url = ch.get("url", "")
                    if url:
                        name = ch.get("name", "未知频道")
                        f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
        
        logger.info(f"✅ M3U 文件已生成: {path}")
    
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
