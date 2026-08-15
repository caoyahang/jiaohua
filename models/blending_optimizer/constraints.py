"""配煤约束定义与校验（方案 4.1.5 输入中的 min/max_ratio、库存、质量目标）。

三类约束：
  1. 配比约束：各煤种 min_ratio/max_ratio 上下限，配比和 = 1
  2. 库存约束：按日耗估算库存可用天数，不得低于安全天数
  3. 质量约束：预测质量须满足 target_quality（M25≥、M10≤、CSR≥、CRI≤）

GA 求解时以罚函数形式并入适应度；求解后用 validate() 做硬校验兜底。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 库存安全可用天数（低于该值的煤种不参与配比，避免方案不可执行）
DEFAULT_MIN_STOCK_DAYS = 3.0
# 约束违反的惩罚权重（罚函数法）
PENALTY_WEIGHT = 1e4


@dataclass
class QualityTarget:
    """目标焦炭质量约束（对应 4.1.5 target_quality）。"""

    M25_min: float = 90.0
    M10_max: float = 6.5
    CSR_min: float = 65.0
    CRI_max: float = 25.0

    def violations(self, predicted: Dict[str, float]) -> List[str]:
        """返回质量约束违反项描述列表（空列表 = 全部满足）。"""
        msgs = []
        if predicted["M25"] < self.M25_min:
            msgs.append(f"M25 {predicted['M25']:.1f} 低于下限 {self.M25_min}")
        if predicted["M10"] > self.M10_max:
            msgs.append(f"M10 {predicted['M10']:.1f} 高于上限 {self.M10_max}")
        if predicted["CSR"] < self.CSR_min:
            msgs.append(f"CSR {predicted['CSR']:.1f} 低于下限 {self.CSR_min}")
        if predicted["CRI"] > self.CRI_max:
            msgs.append(f"CRI {predicted['CRI']:.1f} 高于上限 {self.CRI_max}")
        return msgs


def check_ratio_bounds(ratios: List[float], min_ratios: List[float], max_ratios: List[float]) -> float:
    """配比上下限 + 配比和约束的违反量（0 = 满足）。

    违反量定义：越界绝对值之和 + |配比和 - 1|。
    """
    violation = abs(sum(ratios) - 1.0)
    for r, lo, hi in zip(ratios, min_ratios, max_ratios):
        if r < lo:
            violation += lo - r
        elif r > hi:
            violation += r - hi
    return violation


def check_inventory_days(
    ratios: List[float],
    stock_tons: List[float],
    daily_consumption_tons: float,
    min_stock_days: float = DEFAULT_MIN_STOCK_DAYS,
) -> float:
    """库存可用天数约束的违反量（0 = 满足）。

    煤种 i 可用天数 = 库存_i / (日耗 × 配比_i)；配比为 0 的煤种不检查。
    """
    violation = 0.0
    for r, stock in zip(ratios, stock_tons):
        if r <= 1e-6:
            continue
        days = stock / (daily_consumption_tons * r)
        if days < min_stock_days:
            violation += min_stock_days - days
    return violation


def quality_violation_amount(predicted: Dict[str, float], target: QualityTarget) -> float:
    """质量约束违反量（归一化到百分点，0 = 满足），供罚函数使用。"""
    amount = 0.0
    amount += max(0.0, target.M25_min - predicted["M25"])
    amount += max(0.0, predicted["M10"] - target.M10_max)
    amount += max(0.0, target.CSR_min - predicted["CSR"])
    amount += max(0.0, predicted["CRI"] - target.CRI_max)
    return amount


def penalty(
    ratios: List[float],
    min_ratios: List[float],
    max_ratios: List[float],
    stock_tons: List[float],
    daily_consumption_tons: float,
    predicted_quality: Optional[Dict[str, float]],
    quality_target: QualityTarget,
) -> float:
    """综合罚函数：配比 + 库存 + 质量三类约束违反量的加权和。"""
    total = check_ratio_bounds(ratios, min_ratios, max_ratios) * PENALTY_WEIGHT
    total += check_inventory_days(ratios, stock_tons, daily_consumption_tons) * PENALTY_WEIGHT * 0.1
    if predicted_quality is not None:
        total += quality_violation_amount(predicted_quality, quality_target) * PENALTY_WEIGHT
    return total


def validate(
    blend_ratio: Dict[str, float],
    min_ratios: Dict[str, float],
    max_ratios: Dict[str, float],
    predicted_quality: Dict[str, float],
    quality_target: QualityTarget,
) -> List[str]:
    """方案落库前的硬校验，返回全部违反项描述（空列表 = 方案可行）。"""
    msgs: List[str] = []
    total = sum(blend_ratio.values())
    if abs(total - 1.0) > 1e-3:
        msgs.append(f"配比和 {total:.4f} ≠ 1")
    for name, r in blend_ratio.items():
        lo, hi = min_ratios.get(name, 0.0), max_ratios.get(name, 1.0)
        if r < lo - 1e-6 or r > hi + 1e-6:
            msgs.append(f"{name} 配比 {r:.3f} 超出 [{lo}, {hi}]")
    msgs.extend(quality_target.violations(predicted_quality))
    return msgs
