"""数据质量日报统计（方案§3.3）单元测试。

与 data/pipeline/quality_check.py 的标记口径对齐；
断言值均可手算，覆盖覆盖率/在线率/各标记计数/关键测点/换向剔除。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.pipeline.quality_report import summarize_quality


def _df(values: list, flags: list, reversal: list | None = None) -> pd.DataFrame:
    """构造带标记列的测试 DataFrame。"""
    data: dict = {"temp": values, "temp__flag": flags}
    if reversal is not None:
        data["reversal_flag"] = reversal
    return pd.DataFrame(data)


class TestCoverageAndOnlineRate:
    """覆盖率（测点维度）与在线率（时间维度）口径。"""

    def test_all_good_is_full(self):
        df = pd.DataFrame({
            "temp": [1300.0] * 5,
            "temp__flag": ["good"] * 5,
            "pressure": [100.0] * 5,
            "pressure__flag": ["good"] * 5,
        })
        r = summarize_quality(df, expected_samples=5)
        assert r["tag_count"] == 2
        assert r["coverage_rate"] == 1.0
        assert r["online_rate"] == 1.0
        assert r["alerts"] == []

    def test_missing_lowers_online_rate(self):
        # temp 有 1 个缺失：在线率 = 4/5 = 0.8 < 0.99 → 在线率告警
        df = _df(
            [1300.0, 1300.0, np.nan, 1300.0, 1300.0],
            ["good", "good", "missing", "good", "good"],
        )
        r = summarize_quality(df, expected_samples=5)
        assert r["coverage_rate"] == 1.0  # 该测点仍算「覆盖」（有 ≥1 有效样本）
        assert r["online_rate"] == pytest.approx(0.8)
        assert any("在线率" in a for a in r["alerts"])

    def test_range_err_is_not_effective(self):
        # range_err 在 quality_check 中已置 NaN，不算有效样本
        df = _df([1300.0, np.nan, 1300.0], ["good", "range_err", "good"])
        r = summarize_quality(df, expected_samples=3)
        assert r["online_rate"] == pytest.approx(2 / 3)
        assert r["per_tag"][0]["range_err"] == 1


class TestFlagCounts:
    """各质量标记计数。"""

    def test_counts(self):
        df = _df(
            [1300.0, 1300.0, np.nan, 1300.0, np.nan, 1300.0],
            ["good", "spike_err", "range_err", "interpolated", "missing", "good"],
        )
        row = summarize_quality(df, expected_samples=6)["per_tag"][0]
        assert row["spike_err"] == 1
        assert row["range_err"] == 1
        assert row["interpolated"] == 1
        assert row["missing"] == 1
        # 有效 = good(2) + spike_err(1) + interpolated(1) = 4
        # （range_err/missing 在 quality_check 中值已置 NaN）
        assert row["actual"] == 4


class TestCriticalTags:
    """关键工艺参数须 100% 覆盖。"""

    def test_critical_requires_full_coverage(self):
        df = _df([1300.0, np.nan], ["good", "missing"])
        r = summarize_quality(df, expected_samples=2, critical_tags=["temp"])
        assert any("关键测点 temp" in a for a in r["alerts"])

    def test_critical_full_no_alert(self):
        df = _df([1300.0, 1300.0], ["good", "good"])
        r = summarize_quality(df, expected_samples=2, critical_tags=["temp"])
        assert not any("关键测点 temp" in a for a in r["alerts"])


class TestReversal:
    """换向期剔除量（行级，V1.1 红线 4.2.6）。"""

    def test_reversal_excluded_count(self):
        df = _df(
            [1300.0, 1300.0, 1300.0, 1300.0],
            ["good", "good", "good", "good"],
            reversal=["good", "reversal_excluded", "reversal_excluded", "good"],
        )
        r = summarize_quality(df, expected_samples=4)
        assert r["reversal_excluded_count"] == 2


def test_expected_samples_must_be_positive():
    df = _df([1300.0], ["good"])
    with pytest.raises(ValueError):
        summarize_quality(df, expected_samples=0)
