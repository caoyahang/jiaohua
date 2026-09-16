"""API健康检查集成测试（FastAPI TestClient）。

覆盖：
- GET /health 返回200，且包含status/uptime/dependencies字段
- 无数据库环境（conftest已清空连接串）下status应为degraded
- 业务接口未带token应返回401（认证中间链路可用性验证）
"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_health_returns_200():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "uptime_sec" in body
    assert set(body["dependencies"]) == {"postgres", "redis", "tdengine"}


def test_health_degraded_without_dependencies():
    """依赖未配置必须明确降级，禁止返回假绿色健康状态。"""
    resp = client.get("/health")
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["dependencies"] == {
        "postgres": False,
        "redis": False,
        "tdengine": False,
    }


def test_login_rejects_missing_auth_config(monkeypatch):
    """认证配置缺失时返回503，不得启用默认账号和开发密钥。"""
    monkeypatch.delenv("ADMIN_PASSWORD")
    resp = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 503
    assert "ADMIN_PASSWORD" in resp.json()["detail"]


def test_business_route_requires_auth():
    """未带token访问业务接口应401，证明认证依赖注入已生效。"""
    resp = client.get("/pdm/devices")
    assert resp.status_code == 401


def test_unknown_route_404():
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
