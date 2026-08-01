# IPTV 智能整理平台
全自动 IPTV 直播源采集、测速、验证、分类与自治管理平台。
通过 GitHub Actions 定时运行，无需服务器，永久免费。
# 
## ✨ 功能特点
- 多源聚合 – 自动拉取 10+ 公开 IPTV 源，解析 M3U / TXT，智能去重。
- 双重验证 – HTTP 快速探测 + ffmpeg 深度验证，过滤无效、广告、黑名单 URL。
- 智能分类 – 按央视、卫视、地方（省份）、港澳台自动归类，支持 demo.txt 自定义顺序。
- 固定源保护 – 预设优质源，系统支持自动优化（选择延迟最低的备源），也可锁定禁止替换。
- 自治模式 – 新源先进入候选池，经过多次验证（成功率、延迟）达标后才提升为稳定源，实现“发现-验证-提升”闭环。
- 多格式输出 – 生成 tv.m3u、tv.txt、tv_multi.m3u、channels.json、tv_lite.m3u。
- 完全自动化 – 通过 GitHub Actions 每 6 小时自动运行，输出文件直接托管在仓库中。



# 🚀 快速开始
## 方式一：使用 GitHub Actions（推荐）
1.Fork 本仓库到你的 GitHub 账号。
2.启用 Actions：进入仓库 → Actions 标签 → 点击“I understand my workflows, go ahead and enable them”。
3.手动触发首次运行（可选）：进入 Actions → IPTV 源智能更新与整理 → Run workflow。
4.获取播放列表：
   - 标准 M3U：https://你的用户名.github.io/ITV/output/tv.m3u
   - 标准 TXT：https://你的用户名.github.io/ITV/output/tv.txt
   - JSON API：https://你的用户名.github.io/ITV/output/channels.json
  （替换 你的用户名 为你的 GitHub 账号名）
## 方式二：本地运行（调试用）
### Python 代码
```python
# git clone https://github.com/你的用户名/ITV.git
cd ITV
pip install -r requirements.txt
# 安装 ffmpeg（可选，用于深度验证）
sudo apt-get install ffmpeg   # Ubuntu/Debian
python -m src.run
```

## ⚙️ 配置说明

## 所有配置通过 config/config.yaml 管理，GitHub Actions 中可通过环境变量覆盖。
### 核心配置项
| 功能       | 描述                 | 状态      |
|------------|----------------------|-----------|
   变量               | 默认值              | 说明
 autonomous_mode | true | 是否启用自治模式
 max_workers | 20 | 并发测速线程数
 ffmpeg_enable	| true	| 是否启用 ffmpeg 深度验证
 ffmpeg_mode	deep	| deep |   / quick / off
 candidate_min_success	|  3	|  候选源最少成功次数
 candidate_min_success_rate	|  0.5	|  候选源最低成功率（50%）
 candidate_max_latency	|  3000	|  候选源最大平均延迟（毫秒）
 slow_speed_threshold	|  3000	|  慢速阈值（超过此值不进入稳定版）
 enable_demo_filter	|  true|  	是否按 demo.txt 筛选频道
 max_sources_per_channel	|  3	| 每个频道保留的最大源数量
  
更多配置项请查看 config/config.yaml。

## 📂 输出文件说明
| 文件     | 说明               | 
|------------|----------------------|
output/tv.m3u	  |  标准 M3U 播放列表（按 demo.txt 顺序）
output/tv.txt	TXT 格式（频道名,URL）
output/tv_multi.m3u	  |   多源 M3U（备选地址用 # 分隔）
output/channels.json	 |   JSON API（包含频道名、URL、延迟、编码）
output/tv_lite.m3u	 |   精简版（仅保留各分类前 50 个频道）
data/iptv_cache.db	 |   SQLite 数据库（缓��、候选池、稳定源）


## 🧠 自治模式工作原理
1.采集 → 拉取所有订阅源，解析并去重。
2.测速验证 → HTTP 探测 + ffmpeg 深度验证，过滤无效源。
3.候选池观察 → 新源进入候选池，经多次验证（次数≥3、成功率≥50%、延迟≤3000ms）后标记为稳定。
4.提升 → 稳定候选源替换同名劣质源，记录到稳定池。
5.质量监控 → 稳定源持续检测，连续失败触发告警，自动从候选池寻找替代。

## 🔒 固定源配置
在 src/fixed_sources.py 中预设优质源，系统将优先使用这些源，并支持自动优化（选择延迟最低的备源）或锁定禁止替换。

## 示例：
```python
CCTV_FIXED_SOURCES = {
    "CCTV-1": ["http://example.com/cctv1.m3u8"],
    "CCTV-5+": ["http://example.com/cctv5plus.m3u8"],
}
```

## Docker 部署指南
🚀 快速部署
1. 拉取镜像
```python
docker pull zzgpy/itv:latest
```
2. 一次性运行（手动触发）
```python
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  -e AUTONOMOUS_MODE=true \
  -e FFMPEG_ENABLE=true \
  -e MAX_WORKERS=20 \
  zzgpy/itv:latest
```
参数说明：
- --rm：容器执行完成后自动删除。
- -v $(pwd)/data:/app/data：挂载数据目录，保存缓存和候选池等状态。
- -v $(pwd)/output:/app/output：挂载输出目录，获取生成的播放列表文件。
- -e：覆盖环境变量，可调整运行行为。
  执行完成后，./output 目录下会生成 tv.m3u、tv.txt 等文件。

 ## ⏰ 定时自动运行（推荐）
 方式一：宿主机 crontab（Linux）
 编辑 crontab：
 ```bash
crontab -e
```
添加一行（每天凌晨 2 点执行）：
 ```text
0 2 * * * docker run --rm -v /path/to/data:/app/data -v /path/to/output:/app/output zzgpy/itv:latest
```
替换 /path/to/data 和 /path/to/output 为实际路径。
方式二：Kubernetes CronJob（集群环境）
创建 cronjob.yaml：
 ```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: iptv-collector
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: iptv-collector
            image: zzgpy/itv:latest
            env:
            - name: AUTONOMOUS_MODE
              value: "true"
            - name: FFMPEG_ENABLE
              value: "true"
            volumeMounts:
            - name: data
              mountPath: /app/data
            - name: output
              mountPath: /app/output
          volumes:
          - name: data
            persistentVolumeClaim:
              claimName: iptv-data
          - name: output
            persistentVolumeClaim:
              claimName: iptv-output
          restartPolicy: OnFailure
```
应用：
```
kubectl apply -f cronjob.yaml
```
## 🧩 自定义配置
若需要覆盖默认 config/config.yaml，可挂载自定义配置目录：
```
docker run --rm \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  zzgpy/itv:latest
```
注意：config/ 目录下必须包含 config.yaml、alias.txt、blacklist.txt、demo.txt、subscribe.txt 等文件，否则程序将使用默认配置。
## 🌐 使用 docker-compose（可选）
创建 docker-compose.yml：
```
version: '3'
services:
  iptv-collector:
    image: zzgpy/itv:latest
    container_name: iptv-collector
    restart: "no"
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./config:/app/config   # 可选
    environment:
      - AUTONOMOUS_MODE=true
      - FFMPEG_ENABLE=true
      - MAX_WORKERS=20
```
运行：
```
docker-compose up
```
由于容器执行完成后会退出，如需定时运行，建议用外部 cron 调度 docker-compose run --rm iptv-collector。
## 📦 环境变量说明
| 变量     | 默认值                | 描述    |
|------------|----------------------|-----------|
|AUTONOMOUS_MODE	|true	|启用自治模式（推荐）|
|FFMPEG_ENABLE	|true	|启用 ffmpeg 深度验证|
|FFMPEG_MODE	|deep	|deep / quick / off|
|MAX_WORKERS	|20	|并发测速线程数|
|TIMEOUT	|8	HTTP |请求超时（秒）|
|ENABLE_DEMO_FILTER	|true|	按 demo.txt 筛选频道|
|ENABLE_ALIAS	|true|	启用别名匹配|
|ENABLE_BLACKLIST	|true|	启用黑名单过滤|

完整配置可查看 config/config.yaml 或通过 -e 覆盖。
## 📂 持久化数据说明
- /app/data：数据库缓存、候选池、稳定源记录等状态数据，建议持久化，避免每次重新学习。
- /app/output：生成的播放列表文件（tv.m3u、tv.txt 等），需持久化才能供外部服务访问。

## 📋 自定义频道顺序
编辑 config/demo.txt 即可自定义频道分组和顺序，支持精确匹配、包含匹配、拼音匹配和省份自动归类。

## ⚠️ 免责声明
- 本项目仅用于个人学习和测试，不用于任何商业用途。
- 所有节目源均来自互联网公开链接，项目本身不存储、不篡改任何媒体内容。
- 严禁将本项目及生成的播放列表用于商业传播、二次分发。
- 因违规使用产生的任何法律责任，均由使用者自行承担。

## 📄 许可证
  MIT License

