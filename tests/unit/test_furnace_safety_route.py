"""焦炉控制路由安全出口测试（方案§4.2.6 红线）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from models.furnace_control.safety_limits import (
    COLLECTOR_PRESSURE_LIMIT,
    FLUE_DRAFT_LIMIT,
    GAS_FLOW_LIMIT,
)
from services.api.main import app
from services.api.routes.furnace import _clamp_ai_setpoints


client = TestClient(app)


def _auth_header() -> dict[str, str]:
    """使用测试环境显式配置的账号获取认证头。"""
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_route_clamp_uses_canonical_safety_envelope() -> None:
    """服务层输出必须服从 safety_limits.py 的唯一安全包线。"""
    result = _clamp_ai_setpoints(
        gas_flow=GAS_FLOW_LIMIT.abs_max + 1000.0,
        flue_draft=FLUE_DRAFT_LIMIT.abs_max + 100.0,
        collector_pressure=COLLECTOR_PRESSURE_LIMIT.abs_max + 100.0,
        current_gas_flow=GAS_FLOW_LIMIT.abs_max - 100.0,
        current_flue_draft=FLUE_DRAFT_LIMIT.abs_max - 5.0,
        current_collector_pressure=COLLECTOR_PRESSURE_LIMIT.abs_max - 2.0,
    )

    assert result == {
        "gas_flow": pytest.approx(GAS_FLOW_LIMIT.abs_max),
        "flue_draft": pytest.approx(FLUE_DRAFT_LIMIT.abs_max),
        "collector_pressure": pytest.approx(COLLECTOR_PRESSURE_LIMIT.abs_max),
    }


def test_ai_setpoint_returns_503_instead_of_placeholder() -> None:
    """模型与实时数据未接通时不得返回示例设定值。"""
    response = client.get("/furnace/ai-setpoint?furnace_id=1", headers=_auth_header())
    assert response.status_code == 503
    assert "未就绪" in response.json()["detail"]


def test_control_mode_without_redis_returns_503() -> None:
    """控制模式没有持久化时不得返回成功。"""
    response = client.post(
        "/furnace/control-mode",
        headers=_auth_header(),
        json={
            "furnace_id": 1,
            "mode": "shadow",
            "operator": "测试员",
            "reviewer": "复核员",
            "reason": "安全测试",
            "confirm": True,
        },
    )
    assert response.status_code == 503
    assert "Redis" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "furnace_id": 1,
            "mode": "manual",
            "operator": "测试员",
            "reviewer": "复核员",
            "reason": "禁止软件切手动",
            "confirm": True,
        },
        {
            "furnace_id": 1,
            "mode": "auto",
            "operator": "同一人",
            "reviewer": "同一人",
            "reason": "缺少独立复核",
            "confirm": True,
        },
        {
            "furnace_id": 1,
            "mode": "auto",
            "operator": "测试员",
            "reviewer": "复核员",
            "reason": "未确认",
            "confirm": False,
        },
    ],
)
def test_control_mode_rejects_unsafe_transition(payload: dict[str, object]) -> None:
    """手动软切换、同人复核和未确认请求必须在契约层拒绝。"""
    response = client.post("/furnace/control-mode", headers=_auth_header(), json=payload)
    assert response.status_code == 422
