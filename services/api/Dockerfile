# AI焦化厂智能化平台 - FastAPI后端镜像
FROM python:3.11-slim

WORKDIR /app

# 构建上下文固定为仓库根目录；API 会调用 models/ 与 data/，必须同镜像安装。
COPY pyproject.toml requirements.txt ./
COPY services/ ./services/
COPY data/ ./data/
COPY models/ ./models/
RUN pip install --no-cache-dir .

COPY config/ ./config/

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
