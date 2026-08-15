"""热工K系数单元测试（方案4.2.6节统一考核口径）：

- K均 = (机侧+焦侧合格火道数) / 总测量火道数
- K安 = 相邻班次标准温度波动合格率
- K1  = 推焦计划系数；K2 = 推焦执行系数；K3 = K1 × K2

被测模块：data.pipeline.k_coefficients（数据底座已实现，测试与其真实API对齐）。
"""

import numpy as np
import pandas as pd
import pytest

from data.pipeline import k_coefficients as kc


class TestKJun:
    """K均：直行温度均匀系数 = 合格火道数 / 总测量火道数。"""

    def test_all_qualified_equals_one(self):
        # 10个火道全部在标准温度 ±7℃ 内
        temps = [1300.0, 1302.0, 1305.0, 1298.0, 1301.0,
                 1306.0, 1299.0, 1303.0, 1304.0, 1300.0]
        assert kc.k_jun(temps, standard_temp=1303.0, tolerance=7.0) == pytest.approx(1.0)

    def test_partial_qualified(self):
        # 10个火道中8个合格 → K均 = 0.8
        temps = [1300.0] * 8 + [1320.0, 1280.0]
        assert kc.k_jun(temps, standard_temp=1303.0, tolerance=7.0) == pytest.approx(0.8)

    def test_empty_returns_nan_not_crash(self):
        # 无测量点不允许抛异常，返回 NaN 由上游决定口径
        assert np.isnan(kc.k_jun([], standard_temp=1303.0))


class TestKAn:
    """K安：相邻班次标准温度波动合格率。"""

    def test_range_and_ratio(self):
        # 4对相邻班次，3对波动 ≤5℃ → K安 = 0.75
        pairs = [(1300.0, 1303.0), (1303.0, 1301.0), (1301.0, 1312.0), (1312.0, 1310.0)]
        result = kc.k_an(pairs, tolerance=5.0)
        assert result == pytest.approx(0.75)
        assert 0.0 <= result <= 1.0

    def test_empty_returns_nan(self):
        assert np.isnan(kc.k_an([]))


class TestK123:
    """K1/K2/K3：推焦计划/执行/总系数，K3 必须严格等于 K1 × K2。"""

    def test_k1_k2_individual(self):
        planned = pd.Series([1200.0, 1210.0, 1180.0, 1300.0])   # 计划结焦时间(分钟)
        scheduled = pd.Series([1200.0, 1200.0, 1200.0, 1200.0])  # 规定结焦时间
        # 容差10分钟：偏差[0,10,20,100] → 前2炉符合 → K1 = 0.5
        assert kc.k1(planned, scheduled, tolerance_min=10.0) == pytest.approx(0.5)

        actual_push = pd.Series([100.0, 203.0, 306.0, 500.0])   # 实际推焦时刻
        planned_push = pd.Series([100.0, 200.0, 300.0, 400.0])  # 计划推焦时刻
        # 容差5分钟：偏差[0,3,6,100] → 前2炉符合 → K2 = 0.5
        assert kc.k2(actual_push, planned_push, tolerance_min=5.0) == pytest.approx(0.5)

    def test_k3_equals_k1_times_k2(self):
        planned = pd.Series([1200.0, 1210.0, 1180.0, 1300.0])
        scheduled = pd.Series([1200.0, 1200.0, 1200.0, 1200.0])
        actual_push = pd.Series([100.0, 203.0, 306.0, 500.0])
        planned_push = pd.Series([100.0, 200.0, 300.0, 400.0])

        v1 = kc.k1(planned, scheduled)
        v2 = kc.k2(actual_push, planned_push)
        v3 = kc.k3(planned, scheduled, actual_push, planned_push)
        assert v3 == pytest.approx(v1 * v2, abs=1e-9)
        assert v3 == pytest.approx(0.5 * 0.5, abs=1e-9)

    def test_k3_nan_propagation(self):
        # 空序列 → K1/K2 为 NaN → K3 为 NaN
        empty = pd.Series(dtype=float)
        assert np.isnan(kc.k3(empty, empty, empty, empty))
