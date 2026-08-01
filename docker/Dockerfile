FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（ffmpeg 用于深度验证）
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源码（排除 data，因为 data 在运行时生成）
COPY src/ ./src/
COPY config/ ./config/

# 创建运行时数据目录
RUN mkdir -p data

# 复制入口脚本并设置执行权限
COPY docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 设置环境变量（可通过 docker run -e 覆盖）
ENV AUTONOMOUS_MODE=true \
    OPEN_RTMP=false \
    FFMPEG_ENABLE=true \
    MAX_WORKERS=20

# 暴露端口（可选）
EXPOSE 8080 1935

# 入口点
ENTRYPOINT ["docker-entrypoint.sh"]
