"""全局异常处理（services/AGENTS.md §2 错误语义）。

- HTTPException：交给 FastAPI 默认处理器，保持 {"detail": "中文描述"} 契约不变；
- 其余未捕获异常：统一兜底为 500 {"detail": "服务器内部错误"} 并记日志（含堆栈），
  避免把内部异常细节泄漏给调用方。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器（main.py 装配时调用一次）。"""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未捕获异常: %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
