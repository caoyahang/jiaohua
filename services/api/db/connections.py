"""数据库/缓存连接工厂（方案§3.4 数据底座）。

职责：集中管理 PostgreSQL / TDengine / Redis 的连接创建，路由层不再 inline 驱动连接代码。
约定：
- 驱动一律函数体内懒加载（总纲 §1），未装驱动的环境也能 import 本模块；
- 连接串只从环境变量读（.env，样例见 .env.example），禁止明文密码入库；
- 未配置连接串视为"依赖跳过"（返回 None），连接失败抛 503——与 /health 的
  degraded 语义和 tests/conftest.py 的清库约定配套；
- 连接池化是后续优化项（现状为短连接，QPS 低、自用内网可接受）。
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    import psycopg2.extensions
    import redis
    import taospy

logger = logging.getLogger(__name__)


def mask_url(url: str) -> str:
    """隐藏连接串中的密码（日志输出前必须过此函数，services/AGENTS.md §3）。

    >>> mask_url("postgresql://ai_admin:secret@postgres/coke_plant")
    'postgresql://ai_admin:***@postgres/coke_plant'
    """
    if "@" in url and ":" in url.split("@")[0]:
        head, tail = url.rsplit("@", 1)
        user = head.rsplit(":", 1)[0]
        return f"{user}:***@{tail}"
    return url


def get_pg_conn() -> "psycopg2.extensions.connection":
    """创建 PostgreSQL 连接（调用方负责 close，建议 try/finally）。

    Raises:
        HTTPException: 503 数据库未配置或连接失败。
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="数据库未配置（DATABASE_URL 缺失）")
    try:
        import psycopg2  # noqa: PLC0415  # 懒加载：总纲§1

        return psycopg2.connect(url, connect_timeout=3)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("PostgreSQL连接失败: %s", exc)
        raise HTTPException(status_code=503, detail="数据库不可用") from exc


def get_td_conn() -> "taospy.TaosConnection":
    """创建 TDengine 连接（调用方负责 close）。

    Raises:
        HTTPException: 503 时序库未配置或连接失败。
    """
    url = os.getenv("TDENGINE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="时序库未配置（TDENGINE_URL 缺失）")
    try:
        import taospy  # noqa: PLC0415  # 懒加载：总纲§1

        return taospy.connect(url=url)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("TDengine连接失败: %s", exc)
        raise HTTPException(status_code=503, detail="时序库不可用") from exc


def get_redis() -> "redis.Redis | None":
    """创建 Redis 客户端；未配置或不可用时返回 None（由调用方降级，不抛错）。

    Redis 在本项目只放缓存/会话/告警队列（data/AGENTS.md §3），
    不可用时不应阻断业务接口，故语义与 PG/TD 不同。
    """
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis  # noqa: PLC0415  # 懒加载：总纲§1

        return redis.Redis.from_url(url, socket_timeout=2)
    except Exception as exc:
        logger.error("Redis连接失败: %s", exc)
        return None
