# AI焦化厂智能化平台 - 定时任务Worker镜像
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ ./services/

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    TZ=Asia/Shanghai

CMD ["python", "-m", "services.scheduler.worker"]
