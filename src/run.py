#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from src.config_loader import config
from src.logger import logger
from src.subscribe_manager import SubscribeManager
from src.fetcher import fetch_all_sources_incremental
from src.parser import parse_and_dedupe
from src.speed_tester import test_channels_concurrent
from src.ffmpeg_validator import validate_batch
from src.merger import merge_channels_by_name
from src.blacklist_filter import get_blacklist_filter
from src.demo_filter import filter_and_order_by_demo, parse_demo_order_with_categories
from src.database import get_db_cache
from src.stable.manager import StableManager
from src.generator import generate_outputs_from_demo
from src.special_categories import collect_and_append_special_categories
from src.orchestrator import run_autonomous_mode
from src.fixed_sources import CCTV_FIXED_SOURCES

async def main():
    logger.info("🚀 IPTV 智能整理平台启动")
    db = await get_db_cache()
    stable_mgr = StableManager()

    # 同步固定源到数据库
    for name, urls in CCTV_FIXED_SOURCES.items():
        if isinstance(urls, list) and urls:
            url = urls[0]
        else:
            url = urls
        if url:
            await stable_mgr.set_fixed_source(name, url, auto_optimize=True)  # 默认允许自动优化
    logger.info("📌 固定源已同步到数据库")

    # 获取订阅源
    sub_mgr = SubscribeManager()
    subscribe_urls = sub_mgr.get_all_subscribe_urls()
    sources = subscribe_urls if subscribe_urls else config.raw_sources
    logger.info(f"📋 使用 {len(sources)} 个源")

    # 拉取
    raw_contents = await fetch_all_sources_incremental(sources, db)
    channels_dict = parse_and_dedupe(raw_contents)
    if not channels_dict:
        logger.error("❌ 未获取到任何频道")
        return 1

    # 测速
    valid_channels = await test_channels_concurrent(channels_dict)
    logger.info(f"📊 通过测速的频道数: {len(valid_channels)}")
    if config.ffmpeg_enable and valid_channels:
        valid_channels = await validate_batch(valid_channels)
        logger.info(f"📊 通过ffmpeg验证的频道数: {len(valid_channels)}")

    # 获取固定源（从数据库）
    fixed_sources = await stable_mgr.get_stable_sources()
    # 合并（传入固定源）
    merged_channels = merge_channels_by_name(valid_channels, fixed_sources)
    logger.info(f"📊 合并后的频道数: {len(merged_channels)}")

    # 黑名单过滤
    if config.enable_blacklist:
        blacklist_filter = get_blacklist_filter()
        merged_channels = blacklist_filter.filter_channels(merged_channels)
        logger.info(f"📊 黑名单过滤后: {len(merged_channels)}")

    # Demo筛选
    demo_order = parse_demo_order_with_categories() if config.enable_demo_filter else []
    if config.enable_demo_filter and demo_order:
        ordered_channels, _ = filter_and_order_by_demo(merged_channels)
        logger.info(f"📊 Demo筛选后: {len(ordered_channels)}")
    else:
        ordered_channels = merged_channels

    # 生成输出
    generate_outputs_from_demo(ordered_channels, demo_order)

    # 特殊分类采集
    try:
        await collect_and_append_special_categories(Path(config.output_dir), db)
    except Exception as e:
        logger.warning(f"⚠️ 智能补充采集失败: {e}")

    # 自治模式
    if config.autonomous_mode:
        await run_autonomous_mode(skip_discover=True)

    logger.info("🎉 全部完成！")
    await db.close()
    return 0

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("⚠️ 用户中断")
        sys.exit(1)
