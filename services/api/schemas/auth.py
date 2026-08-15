"""认证相关契约（方案§6.1：FastAPI + JWT）。"""

from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录请求体。"""

    username: str
    password: str


class TokenResponse(BaseModel):
    """登录响应体。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
