# 现场采集镜像（方案§3.2/§3.3）；仅通过 compose field profile 显式启动。
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY services/ ./services/
COPY data/ ./data/
COPY models/ ./models/
RUN pip install --no-cache-dir .

COPY config/ ./config/

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

# 采集执行入口将在质量标记持久化链路接通后由 field profile 启用。
CMD ["python", "-m", "data.collector.worker"]
