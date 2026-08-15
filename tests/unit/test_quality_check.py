"""数据质量校验单元测试（方案3.3节：入库前范围检查、突变检查、缺失插值；
4.2.6节红线：换向前后2~3分钟数据打标记、建模前剔除）。

被测模块：data.pipeline.quality_check（数据底座已实现，测试与其真实API对齐）。
"""

import numpy as np
import pandas as pd
import pytest

from data.pipeline import quality_check as qc


def _temp_df(values, start="2026-01-01 12:00:00", freq="1min"):
    """构造单列火道温度时间序列。"""
    idx = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.DataFrame({"fire_channel_temp": values}, index=idx)


class TestRangeCheck:
    """范围检查：越限值打 range_err 标记并置 NaN。"""

    RANGES = {"fire_channel_temp": (900.0, 1400.0)}

    def test_value_within_range_kept(self):
        df = _temp_df([1300.0, 1310.0])
        out = qc.range_check(df, self.RANGES)
        assert out["fire_channel_temp"].notna().all()
        assert (out["fire_channel_temp__flag"] == qc.FLAG_GOOD).all()

    def test_fault_value_flagged_and_nulled(self):
        # 5000℃ 明显是传感器故障值
        df = _temp_df([1300.0, 5000.0])
        out = qc.range_check(df, self.RANGES)
        assert out["fire_channel_temp"].iloc[0] == pytest.approx(1300.0)
        assert np.isnan(out["fire_channel_temp"].iloc[1])
        assert out["fire_channel_temp__flag"].iloc[1] == qc.FLAG_RANGE_ERR


class TestSpikeCheck:
    """突变检查：单步变化超限打 spike_err 标记（值保留，不置NaN）。"""

    def test_gradual_change_passes(self):
        # 1分钟变化5℃属正常波动
        df = _temp_df([1300.0, 1305.0, 1308.0])
        out = qc.spike_check(df, {"fire_channel_temp": 20.0})
        assert (out["fire_channel_temp__flag"] == qc.FLAG_GOOD).all()

    def test_sudden_jump_flagged(self):
        # 1分钟跳变200℃为异常突变
        df = _temp_df([1300.0, 1500.0, 1302.0])
        out = qc.spike_check(df, {"fire_channel_temp": 20.0})
        assert out["fire_channel_temp__flag"].iloc[0] == qc.FLAG_GOOD
        assert out["fire_channel_temp__flag"].iloc[1] == qc.FLAG_SPIKE_ERR
        # 突变点值保留，交由下游决策
        assert out["fire_channel_temp"].iloc[1] == pytest.approx(1500.0)


class TestReversalWindow:
    """换向期剔除（V1.1红线）：换向前后2~3分钟打 reversal_excluded 标记。"""

    def test_window_points_marked(self):
        # 每分钟一个点，换向事件在 12:00 → 窗口 [11:58, 12:03]（前2后3）
        df = _temp_df(
            [1300.0] * 16, start="2026-01-01 11:50:00", freq="1min"
        )
        out = qc.mark_reversal_window(df, [pd.Timestamp("2026-01-01 12:00:00")])
        flag = out["reversal_flag"]
        marked = flag[flag == qc.FLAG_REVERSAL_EXCLUDED]
        # 前2 + 事件点 + 后3 = 6 个点
        assert len(marked) == 6
        assert marked.index.min() == pd.Timestamp("2026-01-01 11:58:00")
        assert marked.index.max() == pd.Timestamp("2026-01-01 12:03:00")
        # 窗口外保持 good
        assert flag.loc["2026-01-01 11:57:00"] == qc.FLAG_GOOD
        assert flag.loc["2026-01-01 12:04:00"] == qc.FLAG_GOOD

    def test_window_outside_redline_rejected(self):
        # 窗口必须在 2~3 分钟红线区间内，1分钟窗口直接拒绝
        df = _temp_df([1300.0] * 5)
        with pytest.raises(ValueError):
            qc.mark_reversal_window(
                df, [pd.Timestamp("2026-01-01 12:02:00")],
                window_before_minutes=1, window_after_minutes=3,
            )

    def test_filter_for_modeling_excludes_marked(self):
        df = _temp_df([1300.0] * 16, start="2026-01-01 11:50:00", freq="1min")
        marked = qc.mark_reversal_window(df, [pd.Timestamp("2026-01-01 12:00:00")])
        clean = qc.filter_for_modeling(marked)
        assert len(clean) == 16 - 6
        assert pd.Timestamp("2026-01-01 12:00:00") not in clean.index
