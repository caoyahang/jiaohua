# 模型训练镜像（方案§4/§5）；通过 compose training profile 按需运行。
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

ENTRYPOINT ["python", "-m", "models.quality_predictor.train"]
