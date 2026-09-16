"""FastAPI应用入口。

只做装配：注册四大应用路由（blend/furnace/pdm/vision）+ 认证路由，
配置CORS、操作日志中间件、全局异常处理与 /health 健康检查。
连接创建在 services/api/db/connections.py，契约模型在 services/api/schemas/。

启动方式：
    uvicorn services.api.main:app --host 0.0.0.0 --port 8000
"""

import logging
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.api.core.exceptions import register_exception_handlers
from services.api.core.security import router as auth_router
from services.api.db.connections import get_pg_conn, get_redis, get_td_conn, mask_url
from services.api.middleware.operation_log import OperationLogMiddleware
from services.api.routes import blend, furnace, pdm, vision

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

START_TIME = time.time()

app = FastAPI(
    title="AI焦化厂智能化平台 API",
    version="1.1.0",
    description="智能配煤 / 焦炉加热控制 / 设备PdM / 安全视觉 四大应用后端",
)

# 内网自用：允许前端开发机跨域；生产部署收敛到具体前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(OperationLogMiddleware)
register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(blend.router)
app.include_router(furnace.router)
app.include_router(pdm.router)
app.include_router(vision.router)


@app.on_event("startup")
def on_startup():
    """启动日志：打印环境与依赖连通性概览（不阻断启动）。"""
    logger.info("=" * 50)
    logger.info("AI焦化厂智能化平台 API 启动 (v1.1.0)")
    logger.info("DATABASE_URL: %s", mask_url(os.getenv("DATABASE_URL", "未配置")))
    logger.info("TDENGINE_URL: %s", mask_url(os.getenv("TDENGINE_URL", "未配置")))
    logger.info("REDIS_URL:    %s", mask_url(os.getenv("REDIS_URL", "未配置")))
    logger.info("已注册路由: /auth /blend /furnace /pdm /vision /health")
    logger.info("=" * 50)


@app.get("/health", summary="健康检查")
def health():
    """健康检查：自身存活 + 依赖（PostgreSQL/Redis/TDengine）连通性。

    依赖不可达时返回 degraded 而非 500，便于负载均衡探活与运维定位。
    """
    deps = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "tdengine": _check_tdengine(),
    }
    status = "ok" if all(deps.values()) else "degraded"
    return {
        "status": status,
        "uptime_sec": round(time.time() - START_TIME, 1),
        "dependencies": deps,
    }


def _check_postgres() -> bool:
    """PostgreSQL连通性；未配置连接串视为不可用。"""
    if not os.getenv("DATABASE_URL"):
        return False
    try:
        get_pg_conn().close()
        return True
    except HTTPException:
        return False


def _check_redis() -> bool:
    """Redis连通性；未配置连接串视为不可用。"""
    if not os.getenv("REDIS_URL"):
        return False
    r = get_redis()
    if r is None:
        return False
    try:
        return bool(r.ping())
    except Exception:
        return False


def _check_tdengine() -> bool:
    """TDengine连通性；未配置连接串视为不可用。"""
    if not os.getenv("TDENGINE_URL"):
        return False
    try:
        get_td_conn().close()
        return True
    except HTTPException:
        return False
