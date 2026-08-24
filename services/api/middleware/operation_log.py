"""操作日志中间件。

记录每个API请求的：方法、路径、客户端IP、当前用户（若有token）、
响应状态码、耗时。写操作（POST/PUT/DELETE/PATCH）落 PostgreSQL
operation_audit 表（方案§3.4.8），满足审计追溯要求（方案4.4.2 环保合规同样依赖审计）。

注意：不记录请求体，避免泄露密码等敏感信息。
审计落表失败只告警不阻断业务（审计是旁路，不能拖垮主链路）。
"""

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from services.api.core import security as auth

logger = logging.getLogger("operation_log")

# 只审计写操作（方案§3.4.8 口径）
WRITE_METHODS = ("POST", "PUT", "DELETE", "PATCH")


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件：逐请求记录"谁、何时、做了什么、结果如何"。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        user = self._extract_user(request)
        response = await call_next(request)
        elapsed_ms = round((time.time() - start) * 1000, 1)
        # 降噪：未配置 DATABASE_URL 的纯后端开发环境下，依赖库的接口 503 是预期行为
        # （前端自动降级 mock），轮询会刷屏，降为 DEBUG；其余情况保持 INFO
        log_level = (
            logging.DEBUG
            if response.status_code == 503 and not os.getenv("DATABASE_URL")
            else logging.INFO
        )
        logger.log(
            log_level,
            "op | user=%s ip=%s %s %s -> %s (%.1fms)",
            user,
            request.client.host if request.client else "-",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        if request.method in WRITE_METHODS:
            self._write_audit(request, user, response.status_code, int(elapsed_ms))
        return response

    @staticmethod
    def _write_audit(request: Request, user: str, status_code: int, elapsed_ms: int) -> None:
        """写操作落审计表 operation_audit；失败仅记日志（库未配置/连接失败都不阻断业务）。"""
        try:
            from services.api.db.connections import get_pg_conn  # noqa: PLC0415

            conn = get_pg_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO operation_audit"
                        " (username, method, path, client_ip, status_code, elapsed_ms)"
                        " VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            user,
                            request.method,
                            request.url.path,
                            request.client.host if request.client else None,
                            status_code,
                            elapsed_ms,
                        ),
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("审计落表失败（不阻断业务）: %s", exc)

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
