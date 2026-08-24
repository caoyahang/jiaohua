"""配煤优化接口集成测试（方案§4.1.5 输入输出规范、§4.1.6 冷启动经验模型）。

覆盖 POST /blend/optimize：
- 未认证 401
- 正常请求返回三套方案（cost_optimal/quality_stable/balanced），配比和≈1（红线容差1e-3），
  四指标齐全，耗时字段存在（验收口径 <5s，见方案§10.1）
- 配比上下限无可行域时 422
- lab_data 缺化验指标时 422（服务层契约 → 优化器契约的收束校验）

环境要求：需安装 scikit-opt/shap（pyproject.toml 已声明）；
冷启动期无 LightGBM 产物，预测走经验模型，断言按经验模型口径设计。
"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _auth_header() -> dict:
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _optimize_payload() -> dict:
    """四种煤的可行请求（参照 docs/API文档.md §2 示例）。"""
    return {
        "target_quality": {"M25_min": 88.0, "M10_max": 7.0, "CSR_min": 60.0, "CRI_max": 28.0},
        "available_coals": [
            {"coal_id": 1, "name": "气煤", "stock_tons": 5000, "price_per_ton": 1200,
             "min_ratio": 0.05, "max_ratio": 0.40,
             "lab_data": {"Ad": 8.5, "Vdaf": 38.2, "St_d": 0.65, "G": 65, "Y": 12.0, "Rmax": 0.75}},
            {"coal_id": 2, "name": "肥煤", "stock_tons": 4000, "price_per_ton": 1500,
             "min_ratio": 0.10, "max_ratio": 0.40,
             "lab_data": {"Ad": 9.5, "Vdaf": 30.0, "St_d": 0.80, "G": 90, "Y": 25.0, "Rmax": 1.05}},
            {"coal_id": 3, "name": "焦煤", "stock_tons": 6000, "price_per_ton": 1800,
             "min_ratio": 0.20, "max_ratio": 0.50,
             "lab_data": {"Ad": 10.0, "Vdaf": 24.0, "St_d": 0.90, "G": 80, "Y": 16.0, "Rmax": 1.30}},
            {"coal_id": 4, "name": "瘦煤", "stock_tons": 3000, "price_per_ton": 1400,
             "min_ratio": 0.05, "max_ratio": 0.30,
             "lab_data": {"Ad": 9.0, "Vdaf": 15.0, "St_d": 0.70, "G": 40, "Y": 6.0, "Rmax": 1.60}},
        ],
        "max_cost_per_ton": 2000,
        "priority": "cost",
    }


def test_optimize_requires_auth():
    resp = client.post("/blend/optimize", json=_optimize_payload())
    assert resp.status_code == 401


def test_optimize_returns_three_solutions():
    resp = client.post("/blend/optimize", json=_optimize_payload(), headers=_auth_header())
    assert resp.status_code == 200, resp.text
    body = resp.json()

    types = {s["type"] for s in body["solutions"]}
    assert types == {"cost_optimal", "quality_stable", "balanced"}
    assert body["compute_time_ms"] > 0
    assert "model_version" in body

    for sol in body["solutions"]:
        # 配比和=1（红线容差 1e-3，同 tests/unit/test_constraints.py 口径）
        assert abs(sum(sol["blend_ratio"].values()) - 1.0) <= 1e-3
        # 参与配比的煤种必须在上下限内
        bounds = {c["name"]: (c["min_ratio"], c["max_ratio"]) for c in _optimize_payload()["available_coals"]}
        for name, ratio in sol["blend_ratio"].items():
            lo, hi = bounds[name]
            assert lo - 1e-6 <= ratio <= hi + 1e-6
        # 四指标齐全且落在经验模型物理钳位区间内（empirical_model.QUALITY_BOUNDS）
        q = sol["predicted_quality"]
        assert set(q) == {"M25", "M10", "CSR", "CRI"}
        assert 60.0 <= q["M25"] <= 100.0
        assert 3.0 <= q["M10"] <= 12.0
        assert 40.0 <= q["CSR"] <= 80.0
        assert 10.0 <= q["CRI"] <= 40.0
        assert sol["estimated_cost"] > 0
        assert 0.0 < sol["confidence"] <= 1.0

    # 成本最优方案的估算成本不高于质量优先方案（目标权重差异的直接体现）
    costs = {s["type"]: s["estimated_cost"] for s in body["solutions"]}
    assert costs["cost_optimal"] <= costs["quality_stable"] + 1e-6


def test_optimize_infeasible_ratio_bounds_422():
    payload = _optimize_payload()
    for coal in payload["available_coals"]:
        coal["min_ratio"] = 0.30  # Σmin = 1.2 > 1，无可行域
    resp = client.post("/blend/optimize", json=payload, headers=_auth_header())
    assert resp.status_code == 422
    assert "无可行域" in resp.json()["detail"]


def test_optimize_incomplete_lab_data_422():
    payload = _optimize_payload()
    payload["available_coals"][0]["lab_data"] = {"Ad": 8.5}  # 缺 Vdaf/St_d/G/Y/Rmax
    resp = client.post("/blend/optimize", json=payload, headers=_auth_header())
    assert resp.status_code == 422
    assert "优化器契约" in resp.json()["detail"]


def test_optimize_solves_within_5_seconds():
    """验收口径：求解时间 < 5 秒（方案§10.1），以响应字段为准。"""
    resp = client.post("/blend/optimize", json=_optimize_payload(), headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["compute_time_ms"] < 5000
