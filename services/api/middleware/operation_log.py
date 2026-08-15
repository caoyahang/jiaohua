"""操作日志中间件。

记录每个API请求的：方法、路径、客户端IP、当前用户（若有token）、
响应状态码、耗时。自用内网场景先写应用日志，后续可落 PostgreSQL
操作审计表以满足审计追溯要求（方案4.4.2 环保合规同样依赖审计）。

注意：不记录请求体，避免泄露密码等敏感信息。
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from services.api.core import security as auth

logger = logging.getLogger("operation_log")


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件：逐请求记录"谁、何时、做了什么、结果如何"。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        user = self._extract_user(request)
        response = await call_next(request)
        elapsed_ms = round((time.time() - start) * 1000, 1)
        logger.info(
            "op | user=%s ip=%s %s %s -> %s (%.1fms)",
            user,
            request.client.host if request.client else "-",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        # TODO: 关键写操作（POST/PUT/DELETE）落审计表 operation_audit
        return response

    @staticmethod
    def _extract_user(request: Request) -> str:
        """从Authorization头解析用户名；无token或非法时返回anonymous，不阻断请求。"""
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return "anonymous"
        try:
            return auth.verify_token(header[7:])["sub"]
        except Exception:
            return "anonymous"
