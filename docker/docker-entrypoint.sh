#!/bin/sh
set -e

# 如果开启了 RTMP 服务，启动 nginx（需提前配置）
# 本项目中仅执行一次采集并退出，适合定时任务
# 若需要长期运行，可改为循环执行

echo "🚀 Starting IPTV collection..."
python -m src.run

echo "✅ Collection completed. Exiting."
