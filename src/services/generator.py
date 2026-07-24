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
        
        # 如果没有 demo_order，加载默认
        if demo_order is None:
            demo_order = load_demo_order()
        
        # 按 demo 顺序分类 - 只匹配 demo 中存在的频道
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
        """
        按 demo 顺序分类
        只输出 demo.txt 中列出的频道，按 demo 顺序排列
        """
        result = {}
        
        if not demo_order:
            logger.warning("⚠️ demo_order 为空，无法按顺序输出")
            return result
        
        # 构建频道名到频道的映射（精确匹配）
        channel_map = {}
        for ch in channels:
            channel_map[ch["name"]] = ch
        
        # 记录已匹配的频道名
        matched_names = set()
        total_matched = 0
        
        # 按 demo 顺序遍历
        for cat, demo_name in demo_order:
            if cat not in result:
                result[cat] = []
            
            matched_ch = None
            
            # 1. 精确匹配
            if demo_name in channel_map:
                matched_ch = channel_map[demo_name]
                matched_names.add(demo_name)
            else:
                # 2. 模糊匹配
                for name, ch in channel_map.items():
                    if name in matched_names:
                        continue
                    if match_channel_name(name, demo_name):
                        matched_ch = ch
                        matched_names.add(name)
                        break
            
            if matched_ch:
                result[cat].append(matched_ch)
                total_matched += 1
        
        # 统计匹配结果
        logger.info(f"📊 Demo 匹配结果: {total_matched}/{len(demo_order)} 个频道匹配成功")
        
        # 如果有未匹配的频道，记录日志但不输出
        unmatched = [ch for ch in channels if ch["name"] not in matched_names]
        if unmatched:
            logger.info(f"📊 未匹配频道: {len(unmatched)} 个（不输出）")
            # 只显示前10个未匹配的频道名
            if len(unmatched) <= 10:
                for ch in unmatched:
                    logger.debug(f"  未匹配: {ch['name']}")
            else:
                logger.debug(f"  未匹配示例: {', '.join([ch['name'] for ch in unmatched[:10]])} ...")
        
        return result
    
    def _generate_m3u(self, categorized: Dict[str, List[Dict]], path: Path) -> None:
        """生成 M3U - 按 demo 顺序"""
        total = sum(len(ch) for ch in categorized.values())
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Total channels: {total}\n")
            
            for cat, channels in categorized.items():
                if not channels:
                    continue
                # 分类标题注释
                f.write(f"\n# ----- {cat} ({len(channels)}个频道) -----\n")
                for ch in channels:
                    url = ch.get("url", "")
                    if url:
                        name = ch.get("name", "未知频道")
                        f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
        
        logger.info(f"✅ M3U 文件已生成: {path} ({total} 个频道)")
    
    def _generate_txt(self, categorized: Dict[str, List[Dict]], path: Path) -> None:
        """生成 TXT - 按 demo 顺序"""
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
