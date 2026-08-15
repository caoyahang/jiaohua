"""配煤约束单元测试（方案4.1.5节输入规范：各煤种min/max_ratio、
Σ配比=1、库存可用天数、目标质量约束）。

被测模块：models.blending_optimizer.constraints（算法板块已实现，
测试与其真实API对齐——约束以"违反量"（0=满足）与 validate() 硬校验两种形式提供）。

注：吨煤成本是优化目标而非硬约束（上限在 optimizer 罚项中处理），故不在本文件测试。
"""

import pytest

from models.blending_optimizer.constraints import (
    QualityTarget,
    check_inventory_days,
    check_ratio_bounds,
    validate,
)

# 示例煤种（配比上下限参照4.1.5节气煤示例），顺序与下方配比列表一致
MIN_RATIOS = [0.05, 0.15, 0.25, 0.10]   # 气煤/肥煤/焦煤/瘦煤
MAX_RATIOS = [0.20, 0.30, 0.45, 0.30]
COAL_NAMES = ["气煤", "肥煤", "焦煤", "瘦煤"]

GOOD_QUALITY = {"M25": 91.0, "M10": 6.0, "CSR": 66.0, "CRI": 23.0}


class TestRatioBounds:
    """配比上下限 + 配比和约束：违反量 0 = 满足。"""

    def test_valid_ratios_zero_violation(self):
        ratios = [0.15, 0.25, 0.35, 0.25]  # Σ=1.0，均在上下限内
        assert check_ratio_bounds(ratios, MIN_RATIOS, MAX_RATIOS) == pytest.approx(0.0)

    def test_sum_not_one_rejected(self):
        ratios = [0.15, 0.25, 0.35, 0.35]  # Σ=1.10，且瘦煤0.35>max0.30
        # 违反量 = |Σ-1| + 越界量 = 0.10 + 0.05
        assert check_ratio_bounds(ratios, MIN_RATIOS, MAX_RATIOS) == pytest.approx(0.15)

    def test_below_min_rejected(self):
        ratios = [0.02, 0.28, 0.40, 0.30]  # 气煤 0.02 < min 0.05
        assert check_ratio_bounds(ratios, MIN_RATIOS, MAX_RATIOS) > 0.0

    def test_above_max_rejected(self):
        ratios = [0.25, 0.20, 0.35, 0.20]  # 气煤 0.25 > max 0.20
        assert check_ratio_bounds(ratios, MIN_RATIOS, MAX_RATIOS) > 0.0


class TestInventoryDays:
    """库存可用天数约束：配比为0的煤种不检查。"""

    def test_sufficient_stock_passes(self):
        ratios = [0.25, 0.25, 0.25, 0.25]
        stocks = [10000.0] * 4  # 日耗1000吨 → 各煤种可用40天
        assert check_inventory_days(ratios, stocks, daily_consumption_tons=1000.0,
                                    min_stock_days=3.0) == pytest.approx(0.0)

    def test_shortage_flagged(self):
        ratios = [0.25, 0.25, 0.25, 0.25]
        stocks = [10000.0, 500.0, 10000.0, 10000.0]  # 肥煤仅2天 < 3天
        assert check_inventory_days(ratios, stocks, daily_consumption_tons=1000.0,
                                    min_stock_days=3.0) > 0.0

    def test_zero_ratio_coal_skipped(self):
        ratios = [0.0, 0.30, 0.40, 0.30]
        stocks = [0.0, 10000.0, 10000.0, 10000.0]  # 气煤无库存但不参与配比
        assert check_inventory_days(ratios, stocks, daily_consumption_tons=1000.0,
                                    min_stock_days=3.0) == pytest.approx(0.0)


class TestValidate:
    """方案落库前硬校验：返回违反项描述列表（空 = 可行）。"""

    def _mins_maxs(self):
        return dict(zip(COAL_NAMES, MIN_RATIOS)), dict(zip(COAL_NAMES, MAX_RATIOS))

    def test_valid_blend_accepted(self):
        mins, maxs = self._mins_maxs()
        blend = dict(zip(COAL_NAMES, [0.15, 0.25, 0.35, 0.25]))
        assert validate(blend, mins, maxs, GOOD_QUALITY, QualityTarget()) == []

    def test_sum_violation_reported(self):
        mins, maxs = self._mins_maxs()
        blend = dict(zip(COAL_NAMES, [0.15, 0.25, 0.35, 0.35]))  # Σ=1.10
        msgs = validate(blend, mins, maxs, GOOD_QUALITY, QualityTarget())
        assert any("配比和" in m for m in msgs)

    def test_bounds_violation_reported(self):
        mins, maxs = self._mins_maxs()
        blend = dict(zip(COAL_NAMES, [0.02, 0.28, 0.40, 0.30]))  # 气煤低于下限
        msgs = validate(blend, mins, maxs, GOOD_QUALITY, QualityTarget())
        assert any("气煤" in m for m in msgs)

    def test_quality_violation_reported(self):
        mins, maxs = self._mins_maxs()
        blend = dict(zip(COAL_NAMES, [0.15, 0.25, 0.35, 0.25]))
        bad_quality = {"M25": 88.0, "M10": 6.0, "CSR": 63.0, "CRI": 23.0}  # M25/CSR不达标
        msgs = validate(blend, mins, maxs, bad_quality, QualityTarget())
        assert any("M25" in m for m in msgs)
        assert any("CSR" in m for m in msgs)
