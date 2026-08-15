# AI焦化厂智能化平台 - FastAPI后端镜像
FROM python:3.11-slim

WORKDIR /app

# 先装依赖利用构建缓存（requirements.txt在仓库根目录）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝服务代码（模型/数据模块由对应镜像或挂载卷提供）
COPY services/ ./services/

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
