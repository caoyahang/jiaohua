"""告警查询/确认与操作审计的集成测试（方案§3.4.6~3.4.8、docs/API文档.md §5）。

无真实库环境：用 FakePgConn 替换 get_pg_conn（monkeypatch），
断言 SQL 过滤参数与响应映射均符合 API 契约，不做空转断言。
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


class FakeCursor:
    """模拟 psycopg2 cursor：记录最后一条 SQL 与参数，返回预置行。"""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.last_sql = sql
        self.conn.last_params = list(params or [])

    def fetchall(self):
        return self.conn.rows

    @property
    def rowcount(self):
        return self.conn.rowcount


class FakePgConn:
    def __init__(self, rows=(), rowcount=0):
        self.rows = list(rows)
        self.rowcount = rowcount
        self.last_sql = None
        self.last_params = None
        self.committed = False
        self.closed = False

    def cursor(self, cursor_factory=None):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def _auth_header() -> dict:
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


TS = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)

PDM_ROW = {
    "id": 5001, "equipment_id": 101, "level": "WARNING",
    "source": "level2_trend_forecast", "metric": "vibration_speed",
    "metric_value": 7.2, "threshold": 4.5, "iso10816_zone": "C",
    "message": "劣化趋势明显，建议安排检修", "acknowledged": False,
    "handler": None, "ack_comment": None, "acked_at": None, "created_at": TS,
}

VISION_ROW = {
    "id": 9001, "camera_id": "CAM-T01", "scene": "helmet", "area": "焦炉炉顶",
    "label": "no_helmet", "confidence": 0.94, "level": "WARNING",
    "message": "检测到未佩戴安全帽人员", "snapshot_url": "/static/snapshots/9001.jpg",
    "acknowledged": False, "is_false_positive": False, "created_at": TS,
}


# ---------- GET /pdm/alarms ----------

def test_pdm_alarms_requires_auth():
    assert client.get("/pdm/alarms").status_code == 401


def test_pdm_alarms_query_and_mapping(monkeypatch):
    conn = FakePgConn(rows=[PDM_ROW])
    monkeypatch.setattr("services.api.routes.pdm.get_pg_conn", lambda: conn)

    resp = client.get(
        "/pdm/alarms",
        params={"equipment_id": 101, "level": "WARNING", "acknowledged": "false"},
        headers=_auth_header(),
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    it = items[0]
    # 契约字段（API文档§5）：alarm_id/equipment_id/level/source/msg/ts/acknowledged
    assert it["alarm_id"] == 5001
    assert it["equipment_id"] == 101
    assert it["level"] == "WARNING"
    assert it["source"] == "level2_trend_forecast"
    assert it["msg"] == "劣化趋势明显，建议安排检修"
    assert it["acknowledged"] is False
    assert it["ts"].startswith("2026-08-15T08:00:00")
    # 过滤条件确实进入 SQL（防"参数没收进查询"式假实现）
    assert "equipment_id = %s" in conn.last_sql
    assert "level = %s" in conn.last_sql
    assert "acknowledged = %s" in conn.last_sql
    assert conn.last_params == [101, "WARNING", False, 50]
    assert conn.closed


def test_pdm_alarms_illegal_level_422():
    resp = client.get("/pdm/alarms", params={"level": "INFO"}, headers=_auth_header())
    assert resp.status_code == 422


# ---------- GET /vision/alarms ----------

def test_vision_alarms_query_and_mapping(monkeypatch):
    conn = FakePgConn(rows=[VISION_ROW])
    monkeypatch.setattr("services.api.routes.vision.get_pg_conn", lambda: conn)

    resp = client.get(
        "/vision/alarms", params={"scene": "helmet"}, headers=_auth_header()
    )
    assert resp.status_code == 200, resp.text
    it = resp.json()["items"][0]
    assert it["alarm_id"] == 9001
    assert it["scene"] == "helmet"
    assert it["area"] == "焦炉炉顶"
    assert it["camera_id"] == "CAM-T01"
    assert it["snapshot_url"] == "/static/snapshots/9001.jpg"
    assert it["confidence"] == pytest.approx(0.94)
    assert it["acknowledged"] is False
    assert "scene = %s" in conn.last_sql
    assert conn.last_params == ["helmet", 50]


def test_vision_alarms_unknown_scene_422():
    resp = client.get("/vision/alarms", params={"scene": "fire_smoke"}, headers=_auth_header())
    assert resp.status_code == 422


# ---------- POST /vision/alarms/{id}/ack ----------

def test_vision_ack_success(monkeypatch):
    conn = FakePgConn(rowcount=1)
    monkeypatch.setattr("services.api.routes.vision.get_pg_conn", lambda: conn)

    resp = client.post(
        "/vision/alarms/9001/ack",
        json={"handler": "张三", "comment": "已现场核实", "is_false_positive": False},
        headers=_auth_header(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"alarm_id": 9001, "status": "acked"}
    assert "UPDATE vision_alarm" in conn.last_sql
    assert conn.last_params == ["张三", "已现场核实", False, 9001]
    assert conn.committed and conn.closed


def test_vision_ack_not_found_404(monkeypatch):
    conn = FakePgConn(rowcount=0)  # 不存在或已确认
    monkeypatch.setattr("services.api.routes.vision.get_pg_conn", lambda: conn)

    resp = client.post(
        "/vision/alarms/9999/ack",
        json={"handler": "张三"},
        headers=_auth_header(),
    )
    assert resp.status_code == 404


# ---------- 操作审计（中间件落表） ----------

def test_audit_written_on_write_request(monkeypatch):
    """POST 请求落 operation_audit（方案§3.4.8）；记录方法与路径，不含请求体。"""
    conn = FakePgConn()
    monkeypatch.setattr("services.api.db.connections.get_pg_conn", lambda: conn)

    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    assert "INSERT INTO operation_audit" in conn.last_sql
    username, method, path, _ip, status_code, _ms = conn.last_params
    assert (username, method, path) == ("anonymous", "POST", "/auth/login")
    assert status_code == 200
    assert conn.committed


def test_audit_not_written_on_read_request(monkeypatch):
    """GET 请求不落审计表（只记写操作）。"""
    conn = FakePgConn()
    monkeypatch.setattr("services.api.db.connections.get_pg_conn", lambda: conn)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert conn.last_sql is None


def test_audit_failure_does_not_block_business(monkeypatch):
    """审计落表异常（如库不可用）不阻断业务响应。"""
    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("services.api.db.connections.get_pg_conn", _boom)
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200


# ---------- 日志降噪（无库开发环境） ----------

def test_503_without_db_config_logged_below_info(monkeypatch, caplog):
    """DATABASE_URL 未配置时，依赖库接口的 503 轮询降为 DEBUG，不刷 INFO。"""
    monkeypatch.delenv("DATABASE_URL", raising=False)  # conftest 已清，双保险
    import logging

    headers = _auth_header()  # 登录在 caplog 之外完成，避免 200 的 INFO 干扰断言
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="operation_log"):
        # 带 token 访问依赖库的接口，触发真实的 503（数据库未配置）
        resp = client.get("/blend/recipes", headers=headers)
    assert resp.status_code == 503
    infos = [r for r in caplog.records if r.name == "operation_log" and r.levelno >= logging.INFO]
    assert infos == []
    debugs = [r for r in caplog.records if r.name == "operation_log" and r.levelno == logging.DEBUG]
    assert len(debugs) == 1  # 该 503 请求仍留痕，只是降级到 DEBUG


def test_normal_request_still_info(caplog):
    """正常请求的 op 日志保持 INFO 不受影响。"""
    import logging

    with caplog.at_level(logging.DEBUG, logger="operation_log"):
        resp = client.get("/health")
    assert resp.status_code == 200
    infos = [
        r for r in caplog.records
        if r.name == "operation_log" and r.levelno == logging.INFO and "op |" in r.getMessage()
    ]
    assert len(infos) == 1
