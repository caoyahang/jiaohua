"""数据质量校验：范围检查 / 突变检查 / 缺失插值 / 换向期标记剔除。

依据《AI焦化厂智能化落地方案 V1.1》：
- 3.3：入库前自动校验（范围检查、突变检查、缺失插值）
- 4.2.6（V1.1红线）：换向前后2~3分钟的温度/流量/吸力数据为脏数据，
  入库前打标记、建模前剔除——必须在 ETL 管道中实现

约定：所有函数不修改入参，返回带质量标记的新 DataFrame。
标记列：``quality_flag``（good/range_err/spike_err/interpolated/missing/reversal_excluded）。
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 质量标记枚举（写入 quality_flag 列）
FLAG_GOOD = "good"
FLAG_RANGE_ERR = "range_err"
FLAG_SPIKE_ERR = "spike_err"
FLAG_INTERPOLATED = "interpolated"
FLAG_MISSING = "missing"
FLAG_REVERSAL_EXCLUDED = "reversal_excluded"

# 换向期标记对建模不可用（建模前剔除），但入库保留以便追溯
EXCLUDE_FOR_MODELING = {FLAG_RANGE_ERR, FLAG_MISSING, FLAG_REVERSAL_EXCLUDED}


def range_check(
    df: pd.DataFrame,
    ranges: Dict[str, Tuple[float, float]],
    value_col_prefix: str = "",
) -> pd.DataFrame:
    """物理范围检查：超出硬范围的值打 range_err 标记并置 NaN。

    Args:
        df: 含时间序列数据的 DataFrame（列为物理量名）。
        ranges: {列名: (下限, 上限)}，如 {"fire_channel_temp": (900.0, 1400.0)}。
        value_col_prefix: 列名前缀（如点位分级时使用）。

    Returns:
        新 DataFrame：越限值置 NaN，并新增 ``<列名>__flag`` 标记列。
    """
    out = df.copy()
    for col, (lo, hi) in ranges.items():
        col = value_col_prefix + col
        if col not in out.columns:
            continue
        flag_col = f"{col}__flag"
        out[flag_col] = FLAG_GOOD
        bad = (out[col] < lo) | (out[col] > hi)
        if bad.any():
            logger.warning("范围检查越限: %s 共 %d 点（允许 %.2f~%.2f）", col, bad.sum(), lo, hi)
            out.loc[bad, flag_col] = FLAG_RANGE_ERR
            out.loc[bad, col] = np.nan
    return out


def spike_check(
    df: pd.DataFrame,
    max_step: Dict[str, float],
) -> pd.DataFrame:
    """突变检查：相邻采样点单步变化超过上限时打 spike_err 标记。

    突变点不置 NaN（可能是真实工况跳变），仅打标记交由下游决策；
    与范围检查叠加时以后打的标记为准（标记列复用 ``<列名>__flag``）。

    Args:
        df: 时间序列 DataFrame（需按时间排序）。
        max_step: {列名: 单步最大允许变化量}，见 settings.yaml quality_check.spike。

    Returns:
        新 DataFrame，更新 ``<列名>__flag`` 标记列。
    """
    out = df.copy()
    for col, step in max_step.items():
        if col not in out.columns:
            continue
        flag_col = f"{col}__flag"
        if flag_col not in out.columns:
            out[flag_col] = FLAG_GOOD
        diff = out[col].diff().abs()
        spike = diff > step
        if spike.any():
            logger.warning("突变检查超限: %s 共 %d 点（单步上限 %.3f）", col, spike.sum(), step)
            out.loc[spike, flag_col] = FLAG_SPIKE_ERR
    return out


def interpolate_missing(
    df: pd.DataFrame,
    columns: Sequence[str],
    max_gap_seconds: int = 300,
    method: str = "linear",
) -> pd.DataFrame:
    """缺失插值：缺口 ≤ max_gap_seconds 做插值并打 interpolated 标记，超出打 missing。

    Args:
        df: 以 DatetimeIndex 为索引的时间序列 DataFrame。
        columns: 参与插值的列。
        max_gap_seconds: 可插值的最大缺口（秒），见 settings.yaml（默认300）。
        method: 插值方法（默认 linear）。

    Returns:
        新 DataFrame，更新 ``<列名>__flag`` 标记列。
    """
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        raise TypeError("interpolate_missing 要求 DatetimeIndex")
    median_dt = out.index.to_series().diff().median()
    if pd.isna(median_dt):
        return out
    max_gap_points = max(1, int(max_gap_seconds / median_dt.total_seconds()))

    for col in columns:
        if col not in out.columns:
            continue
        flag_col = f"{col}__flag"
        if flag_col not in out.columns:
            out[flag_col] = FLAG_GOOD
        # 连续缺失段长度统计
        is_na = out[col].isna()
        grp = (~is_na).cumsum()
        gap_len = is_na.groupby(grp).cumsum()
        short_gap = is_na & (gap_len <= max_gap_points)
        long_gap = is_na & ~short_gap
        if short_gap.any():
            out[col] = out[col].interpolate(method=method, limit=max_gap_points)
            still_na = out[col].isna()
            out.loc[short_gap & ~still_na, flag_col] = FLAG_INTERPOLATED
            # 段首段尾插值不到的位置归入 missing
            out.loc[short_gap & still_na, flag_col] = FLAG_MISSING
        if long_gap.any():
            out.loc[long_gap, flag_col] = FLAG_MISSING
            logger.warning("缺失缺口超 %ds，标记 missing: %s 共 %d 点",
                           max_gap_seconds, col, long_gap.sum())
    return out


def mark_reversal_window(
    df: pd.DataFrame,
    reversal_events: Iterable[pd.Timestamp],
    window_before_minutes: int = 2,
    window_after_minutes: int = 3,
) -> pd.DataFrame:
    """换向期数据标记（V1.1红线，4.2.6）。

    焦炉换向（煤气/空气交换）前后 2~3 分钟内，温度/流量/吸力数据剧烈
    波动且无控制意义，为脏数据：入库前打 ``reversal_excluded`` 标记，
    建模前由 ``filter_for_modeling`` 剔除。

    Args:
        df: 以 DatetimeIndex 为索引的时间序列 DataFrame。
        reversal_events: 换向事件时间戳序列（来自换向机构状态点位
            reversal_status 的上升沿，见 dcs_tags.yaml）。
        window_before_minutes: 事件前剔除窗口（默认2分钟，红线区间2~3）。
        window_after_minutes: 事件后剔除窗口（默认3分钟，红线区间2~3）。

    Returns:
        新 DataFrame，新增/更新 ``reversal_flag`` 列：窗口内为
        reversal_excluded，窗口外为 good。
    """
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        raise TypeError("mark_reversal_window 要求 DatetimeIndex")
    if not 2 <= window_before_minutes <= 3 or not 2 <= window_after_minutes <= 3:
        raise ValueError("换向期剔除窗口必须在 2~3 分钟红线区间内")

    events = [pd.Timestamp(ts) for ts in reversal_events]
    flag = pd.Series(FLAG_GOOD, index=out.index, name="reversal_flag")
    before = pd.Timedelta(minutes=window_before_minutes)
    after = pd.Timedelta(minutes=window_after_minutes)
    excluded = 0
    for ts in events:
        mask = (out.index >= ts - before) & (out.index <= ts + after)
        flag.loc[mask] = FLAG_REVERSAL_EXCLUDED
        excluded += int(mask.sum())
    out["reversal_flag"] = flag
    if excluded:
        logger.info(
            "换向期标记: %d 次换向事件，共 %d 点打 reversal_excluded（前%d后%d分钟）",
            len(events), excluded, window_before_minutes, window_after_minutes,
        )
    return out


def filter_for_modeling(
    df: pd.DataFrame,
    flag_cols: Optional[List[str]] = None,
    reversal_flag_col: str = "reversal_flag",
) -> pd.DataFrame:
    """建模前过滤：剔除换向期、范围越限、无法插值的缺失点。

    Args:
        df: 经过上述校验（含标记列）的 DataFrame。
        flag_cols: 参与过滤的 ``<列名>__flag`` 列；为 None 时自动发现。
        reversal_flag_col: 换向标记列名。

    Returns:
        仅保留可用于建模的行的 DataFrame（spike_err/interpolated 保留，
        由模型侧自行加权）。
    """
    out = df
    if reversal_flag_col in out.columns:
        out = out[out[reversal_flag_col] != FLAG_REVERSAL_EXCLUDED]
    if flag_cols is None:
        flag_cols = [c for c in out.columns if c.endswith("__flag")]
    for col in flag_cols:
        out = out[~out[col].isin(EXCLUDE_FOR_MODELING)]
    return out
