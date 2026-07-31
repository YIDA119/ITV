from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime
from src.config_loader import config
from src.logger import logger

def generate_m3u(category_channels: Dict[str, List[dict]], category_order: List[str], output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat in category_order:
            for ch in category_channels.get(cat, []):
                url = ch.get("url") or (ch.get("urls") and ch["urls"][0]) or ""
                if url:
                    name = ch.get("demo_name") or ch.get("name", "未知频道")
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
    logger.info(f"✅ M3U 文件已生成: {output_path}")

def generate_txt(category_channels: Dict[str, List[dict]], category_order: List[str], output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        for cat in category_order:
            channels = category_channels.get(cat, [])
            if not channels: continue
            f.write(f"{cat},#genre#\n")
            for ch in channels:
                url = ch.get("url") or (ch.get("urls") and ch["urls"][0]) or ""
                if url:
                    name = ch.get("demo_name") or ch.get("name", "未知频道")
                    f.write(f"{name},{url}\n")
    logger.info(f"✅ TXT 文件已生成: {output_path}")

def generate_multi_m3u(category_channels: Dict[str, List[dict]], category_order: List[str], output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat in category_order:
            for ch in category_channels.get(cat, []):
                urls = ch.get("urls") or [ch.get("url")]
                valid = [u for u in urls if u and u.startswith(('http://','https://'))]
                if valid:
                    name = ch.get("demo_name") or ch.get("name", "未知频道")
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{" # ".join(valid)}\n')
    logger.info(f"✅ 多源 M3U 文件已生成: {output_path}")

def generate_json_api(channels: List[dict], output_path: Path) -> None:
    data = {
        "version": "2.0",
        "total": len(channels),
        "generated": datetime.now().isoformat(),
        "channels": [
            {
                "name": ch["name"],
                "urls": ch.get("urls", [ch.get("url")]),
                "latency": ch.get("latency"),
                "codec": ch.get("video_codec", ""),
                "category": ch.get("demo_category", ch.get("group_title", ""))
            } for ch in channels
        ]
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ JSON API 已生成: {output_path}")

def generate_lite_version(category_channels: Dict[str, List[dict]], output_path: Path) -> None:
    lite = []
    cat_counts = {}
    for cat, chs in category_channels.items():
        for ch in chs:
            if cat == "央视":
                lite.append(ch)
            else:
                if cat_counts.get(cat, 0) < 50:
                    lite.append(ch)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n# 精简版\n")
        for ch in lite:
            url = ch.get("url") or (ch.get("urls") and ch["urls"][0]) or ""
            if url:
                cat = ch.get("demo_category", ch.get("group_title", ""))
                f.write(f'#EXTINF:-1 group-title="{cat}",{ch["name"]}\n{url}\n')
    logger.info(f"✅ 精简版已生成: {output_path}")

def generate_outputs_from_demo(ordered_channels: List[dict], demo_order: List[Tuple[str, str]]) -> None:
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return
    demo_category_order = []
    seen = set()
    for cat, _ in demo_order:
        if cat not in seen:
            seen.add(cat)
            demo_category_order.append(cat)
    filtered = [ch for ch in ordered_channels if ch.get("demo_category") in seen]
    if not filtered:
        logger.warning("过滤后无频道，跳过输出")
        return
    category_channels = {}
    for ch in filtered:
        cat = ch.get("demo_category", "其他")
        category_channels.setdefault(cat, []).append(ch)
    final_order = demo_category_order
    config.output_dir.mkdir(parents=True, exist_ok=True)
    generate_m3u(category_channels, final_order, config.output_dir / "tv.m3u")
    generate_txt(category_channels, final_order, config.output_dir / "tv.txt")
    generate_multi_m3u(category_channels, final_order, config.output_dir / "tv_multi.m3u")
    if config.enable_json_output:
        generate_json_api(filtered, config.output_dir / "channels.json")
    if config.enable_lite_version:
        generate_lite_version(category_channels, config.output_dir / "tv_lite.m3u")
    if config.enable_epg_output:
        # 生成EPG兼容版（同标准M3U）
        generate_m3u(category_channels, final_order, config.output_dir / "tv_epg.m3u")
