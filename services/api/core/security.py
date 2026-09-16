"""最简JWT认证模块（自用内网场景，无RBAC）。

设计说明：
- 技术栈第6.1节未引入第三方JWT库，这里用标准库 hmac/hashlib 手写 HS256 JWT，
  满足内网自用场景的签发/校验需求，不引入额外依赖。
- 账号为单管理员账号（环境变量配置），后续如需多用户可迁移到 PostgreSQL 用户表。
- 操作日志由 middleware/operation_log.py 统一记录，本模块只负责签发与校验。
- 请求/响应契约在 services/api/schemas/auth.py（本文件只做逻辑）。

环境变量（见 .env.example）：
- JWT_SECRET_KEY: 签名密钥
- JWT_EXPIRE_MINUTES: token有效期（分钟），默认480
- ADMIN_USERNAME / ADMIN_PASSWORD: 管理员账号（必须显式配置）
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.api.schemas.auth import LoginRequest, TokenResponse

logger = logging.getLogger(__name__)

EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

router = APIRouter(prefix="/auth", tags=["认证"])
_bearer = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    """Base64URL编码（无padding）。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """Base64URL解码（自动补padding）。"""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: str) -> str:
    """HMAC-SHA256签名。"""
    secret_key = _required_env("JWT_SECRET_KEY")
    digest = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _required_env(name: str) -> str:
    """读取认证必需环境变量，缺失时拒绝提供认证服务。

    Args:
        name: 环境变量名。

    Returns:
        非空的环境变量值。

    Raises:
        HTTPException: 配置缺失时返回 503，禁止退回开发默认凭据。
    """
    value = os.getenv(name, "").strip()
    if not value:
        logger.error("认证配置缺失: %s", name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"认证服务未配置（{name} 缺失）",
        )
    return value


def create_token(username: str) -> str:
    """签发JWT（HS256，含exp/iat/sub声明）。"""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url_encode(
        json.dumps({"sub": username, "iat": now, "exp": now + EXPIRE_MINUTES * 60}).encode()
    )
    return f"{header}.{payload}.{_sign(f'{header}.{payload}')}"


def verify_token(token: str) -> dict:
    """校验JWT签名与有效期，返回payload；非法则抛401。

    使用 hmac.compare_digest 做常量时间比较，防时序攻击。
    """
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token格式非法")
    expected = _sign(f"{header}.{payload}")
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token签名无效")
    claims = json.loads(_b64url_decode(payload))
    if claims.get("exp", 0) < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token已过期")
    return claims


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """FastAPI依赖注入：从Authorization头解析并校验token，返回用户名。"""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="缺少Authorization头")
    return verify_token(credentials.credentials)["sub"]


@router.post("/login", response_model=TokenResponse, summary="登录签发token")
def login(req: LoginRequest) -> TokenResponse:
    """校验账号密码，签发JWT。失败统一返回401，不区分用户不存在/密码错误。"""
    # TODO: 多用户需求出现时迁移到PostgreSQL用户表（含密码哈希pbkdf2/bcrypt）
    admin_username = _required_env("ADMIN_USERNAME")
    admin_password = _required_env("ADMIN_PASSWORD")
    username_ok = hmac.compare_digest(req.username, admin_username)
    password_ok = hmac.compare_digest(req.password, admin_password)
    if not username_ok or not password_ok:
        logger.warning("登录失败: username=%s", req.username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    logger.info("登录成功: username=%s", req.username)
    return TokenResponse(access_token=create_token(req.username), expires_in=EXPIRE_MINUTES * 60)
