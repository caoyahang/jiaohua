"""热工 K 系数计算：K均 / K安 / K1 / K2 / K3。

定义严格按《AI焦化厂智能化落地方案 V1.1》4.2.6：

- K均：直行温度均匀系数 =（机侧+焦侧合格火道数）/ 总测量火道数
- K安：直行温度安定系数（相邻班次标准温度波动合格率）
- K1：推焦计划系数（计划结焦时间与规定结焦时间符合率）
- K2：推焦执行系数（实际推焦时间与计划时间符合率）
- K3 = K1 × K2，推焦总系数（排产核心KPI，见4.5：K3 ≥ 0.95）

数据来源：直行温度测量记录、推焦电流记录、推焦计划表（依赖数据底座）。
判定容差默认值取自 config/settings.yaml 的 k_coefficients 段。
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 默认判定容差（与 config/settings.yaml k_coefficients 段保持一致）
DEFAULT_TEMP_QUALIFIED_TOLERANCE = 7.0    # K均：直行温度合格偏差 ±℃
DEFAULT_K_AN_SHIFT_TOLERANCE = 5.0        # K安：相邻班次标准温度波动判定偏差 ±℃
DEFAULT_COKING_PLAN_TOLERANCE_MIN = 10.0  # K1：计划结焦时间符合判定容差（分钟）
DEFAULT_PUSH_PLAN_TOLERANCE_MIN = 5.0     # K2：实际推焦时间符合判定容差（分钟）


def k_jun(
    measured_temps: Sequence[float],
    standard_temp: float,
    tolerance: float = DEFAULT_TEMP_QUALIFIED_TOLERANCE,
) -> float:
    """K均：直行温度均匀系数。

    =（机侧+焦侧合格火道数）/ 总测量火道数。
    合格 = |实测直行温度 - 标准温度| ≤ tolerance。

    Args:
        measured_temps: 某次直行温度测量的全部火道温度（机侧+焦侧合并，℃）。
        standard_temp: 标准温度（℃）。
        tolerance: 合格判定偏差（±℃，默认7）。

    Returns:
        K均 ∈ [0, 1]；无测量点时返回 NaN。

    TODO: 换向期/修门期火道是否计入总测量火道数按厂热工规程确认；
    建模/考核数据须先用 quality_check 剔除换向期脏数据（4.2.6红线）。
    """
    temps = np.asarray(list(measured_temps), dtype=float)
    temps = temps[~np.isnan(temps)]
    if temps.size == 0:
        return float("nan")
    qualified = np.abs(temps - standard_temp) <= tolerance
    return float(qualified.sum() / temps.size)


def k_an(
    shift_standard_temps: Sequence[Tuple[float, float]],
    tolerance: float = DEFAULT_K_AN_SHIFT_TOLERANCE,
) -> float:
    """K安：直行温度安定系数。

    = 相邻班次标准温度波动合格的班次数 / 考核班次数。
    合格 = |本班标准温度 - 上一班标准温度| ≤ tolerance。

    Args:
        shift_standard_temps: [(班次A标准温度, 班次B标准温度), ...]
            每个元素是一对相邻班次的标准温度（℃）。
        tolerance: 波动判定偏差（±℃，默认5）。

    Returns:
        K安 ∈ [0, 1]；无班次对时返回 NaN。
    """
    pairs = [(a, b) for a, b in shift_standard_temps
             if not (np.isnan(a) or np.isnan(b))]
    if not pairs:
        return float("nan")
    qualified = sum(1 for a, b in pairs if abs(a - b) <= tolerance)
    return float(qualified / len(pairs))


def k1(
    planned_coking_times: pd.Series,
    scheduled_coking_times: pd.Series,
    tolerance_min: float = DEFAULT_COKING_PLAN_TOLERANCE_MIN,
) -> float:
    """K1：推焦计划系数。

    = 计划结焦时间与规定结焦时间符合的炉数 / 计划总炉数。
    符合 = |计划结焦时间 - 规定结焦时间| ≤ tolerance_min。

    Args:
        planned_coking_times: 各炉计划结焦时间（分钟）。
        scheduled_coking_times: 各炉规定结焦时间（分钟），与上者按炉对齐。
        tolerance_min: 符合判定容差（分钟，默认10）。

    Returns:
        K1 ∈ [0, 1]；无炉次时返回 NaN。
    """
    diff = (planned_coking_times - scheduled_coking_times).abs().dropna()
    if diff.empty:
        return float("nan")
    return float((diff <= tolerance_min).mean())


def k2(
    actual_push_times: pd.Series,
    planned_push_times: pd.Series,
    tolerance_min: float = DEFAULT_PUSH_PLAN_TOLERANCE_MIN,
) -> float:
    """K2：推焦执行系数。

    = 实际推焦时间与计划时间符合的炉数 / 执行总炉数。
    符合 = |实际推焦时刻 - 计划推焦时刻| ≤ tolerance_min。

    Args:
        actual_push_times: 各炉实际推焦时刻（分钟偏移或分钟数）。
        planned_push_times: 各炉计划推焦时刻，与上者按炉对齐。
        tolerance_min: 符合判定容差（分钟，默认5）。

    Returns:
        K2 ∈ [0, 1]；无炉次时返回 NaN。
    """
    diff = (actual_push_times - planned_push_times).abs().dropna()
    if diff.empty:
        return float("nan")
    return float((diff <= tolerance_min).mean())


def k3(
    planned_coking_times: pd.Series,
    scheduled_coking_times: pd.Series,
    actual_push_times: pd.Series,
    planned_push_times: pd.Series,
    **kwargs: float,
) -> float:
    """K3：推焦总系数 = K1 × K2（排产核心KPI，目标 ≥0.95，见4.5）。

    Args:
        同 k1 / k2 的参数；**kwargs 透传容差覆盖（如 k1_tolerance_min）。
        为保持签名简单，这里直接复用 k1/k2 默认容差；如需覆盖请分别
        调用 k1/k2 后相乘。

    Returns:
        K3 ∈ [0, 1]；K1 或 K2 为 NaN 时返回 NaN。
    """
    _ = kwargs  # 预留扩展位，避免后续加参数破坏签名
    v1 = k1(planned_coking_times, scheduled_coking_times)
    v2 = k2(actual_push_times, planned_push_times)
    if np.isnan(v1) or np.isnan(v2):
        return float("nan")
    return float(v1 * v2)


def compute_all(
    measured_temps: Sequence[float],
    standard_temp: float,
    shift_standard_temps: Sequence[Tuple[float, float]],
    planned_coking_times: Optional[pd.Series] = None,
    scheduled_coking_times: Optional[pd.Series] = None,
    actual_push_times: Optional[pd.Series] = None,
    planned_push_times: Optional[pd.Series] = None,
) -> Dict[str, float]:
    """一次算齐 K均/K安/K1/K2/K3，供驾驶舱与加热控制统一考核口径。

    推焦序列参数缺省时对应系数返回 NaN（数据底座未接入推焦计划表前
    的常见情况，见4.2.6数据来源说明）。
    """
    result: Dict[str, float] = {
        # 字段名与 API 契约一致（docs/API文档.md §GET /furnace/k-coefficients）：
        # k_uniform / k_stable / k1 / k2 / k3
        "k_uniform": k_jun(measured_temps, standard_temp),
        "k_stable": k_an(shift_standard_temps),
        "k1": float("nan"),
        "k2": float("nan"),
        "k3": float("nan"),
    }
    if (planned_coking_times is not None and scheduled_coking_times is not None
            and actual_push_times is not None and planned_push_times is not None):
        result["k1"] = k1(planned_coking_times, scheduled_coking_times)
        result["k2"] = k2(actual_push_times, planned_push_times)
        result["k3"] = k3(
            planned_coking_times, scheduled_coking_times,
            actual_push_times, planned_push_times,
        )
    else:
        logger.info("推焦计划/执行数据未提供，K1/K2/K3 返回 NaN")
    return result
