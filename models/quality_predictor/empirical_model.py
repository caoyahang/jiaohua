"""经验配煤模型 —— V1.1 冷启动核心（方案 4.1.3 / 4.1.6）。

背景（V1.1 决议）：新厂无历史数据，配煤比+化验数据是各厂核心商业机密，
外购/交换数据基本不可行。投产前（0~6月）以公开文献的经验配煤模型打底：
  - CBRI（印度中央燃料研究所）配煤经验公式
  - 新日铁（NSC）配煤法
  - 鞍山热能院煤岩配煤模型（镜质组反射率分布 + 活惰比）

本模块将上述方法抽象为「单种煤指标加权 + 经验修正项」的透明线性模型，
所有系数集中在 EMPIRICAL_COEFFICIENTS 中，可配置、可标定。

⚠️ 标定 TODO：系数当前取公开文献的典型区间中值，必须用本厂 40kg/200kg
试验焦炉 DOE 数据（60~100炉）回归标定，并标定小焦炉与生产大炉之间
CSR/CRI 的系统偏差（见方案 4.1.6 试生产阶段要求）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger(__name__)

# 预测的四个焦炭质量指标
TARGETS = ("M25", "M10", "CSR", "CRI")

# ---------------------------------------------------------------------------
# 经验公式系数（可配置；以下为公开文献典型值，必须用本厂 DOE 数据标定）
# 结构：{指标: {"bias": 截距, 特征名: 系数}}
# 特征取配合煤加权平均指标：Ad/Vdaf/St_d/G/Y/Rmax_mean/active_inert_ratio
# TODO(标定): 用 DOE 试验数据最小二乘拟合以下系数，并给出置信区间
# TODO(标定): 增加结焦时间/火道温度/熄焦方式等工艺修正项（CSR 可差 3~5 点）
# ---------------------------------------------------------------------------
DEFAULT_COEFFICIENTS: Dict[str, Dict[str, float]] = {
    # 抗碎强度 M25：随粘结指数 G、胶质层厚度 Y 增大而增大，随挥发分增大而降低
    "M25": {"bias": 55.0, "G": 0.35, "Y": 0.6, "Vdaf": -0.25, "Ad": -0.4},
    # 耐磨强度 M10：越低越好；高挥发分、低粘结恶化 M10
    "M10": {"bias": 12.0, "G": -0.06, "Y": -0.10, "Vdaf": 0.05, "Ad": 0.08},
    # 反应后强度 CSR：CBRI 法中 CSR 与煤阶(Rmax)、粘结性正相关，与灰分/惰性质负相关
    "CSR": {"bias": 20.0, "Rmax_mean": 25.0, "G": 0.20, "Y": 0.5,
            "Vdaf": -0.35, "Ad": -0.6, "active_inert_ratio": 2.0},
    # 反应性 CRI：与 CSR 大致镜像；高挥发分、高碱金属灰分加剧反应性
    "CRI": {"bias": 45.0, "Rmax_mean": -10.0, "G": -0.10, "Y": -0.20,
            "Vdaf": 0.20, "Ad": 0.30, "active_inert_ratio": -1.0},
}

# 物理合理性钳位范围（防止经验公式外推失真）
QUALITY_BOUNDS: Dict[str, tuple] = {
    "M25": (60.0, 100.0),
    "M10": (3.0, 12.0),
    "CSR": (40.0, 80.0),
    "CRI": (10.0, 40.0),
}


@dataclass
class SingleCoal:
    """单种煤化验指标（对应方案 4.1.5 输入中的 lab_data）。"""

    name: str
    Ad: float          # 灰分(干基) %
    Vdaf: float        # 挥发分(干燥无灰基) %
    St_d: float        # 全硫(干基) %
    G: float           # 粘结指数
    Y: float           # 胶质层厚度 mm
    Rmax: float        # 镜质组平均最大反射率 %
    # 镜质组反射率分布直方图（0.5~2.0 分段占比），V1.1 修正：单值 Rmax
    # 表达不了混配后反射率分布的"凹口"，经验模型侧先预留接口
    rmax_histogram: Optional[List[float]] = None
    active_ratio: Optional[float] = None  # 活性物含量(煤岩定量) %
    inert_ratio: Optional[float] = None   # 惰性物含量 %


class EmpiricalQualityPredictor:
    """经验配煤质量预测器。

    与 LightGBM 模型保持一致的 predict 接口：输入配煤方案（煤种+配比），
    输出 {M25, M10, CSR, CRI} 四个指标预测值，供配煤优化器作为适应度函数调用。
    """

    def __init__(self, coefficients: Optional[Mapping[str, Mapping[str, float]]] = None):
        """初始化。

        :param coefficients: 自定义系数表，结构同 DEFAULT_COEFFICIENTS；
            为 None 时使用默认文献系数。标定后的系数应从配置文件注入。
        """
        merged: Dict[str, Dict[str, float]] = {k: dict(v) for k, v in DEFAULT_COEFFICIENTS.items()}
        if coefficients:
            for target, coefs in coefficients.items():
                if target in merged:
                    merged[target].update(coefs)
                else:
                    logger.warning("未知指标 %s 的系数被忽略", target)
        self.coefficients = merged

    # ------------------------------------------------------------------ #
    # 特征计算
    # ------------------------------------------------------------------ #
    @staticmethod
    def _blend_features(coals: List[SingleCoal], ratios: List[float]) -> Dict[str, float]:
        """由单种煤指标与配比计算配合煤加权特征。

        配合煤指标 = Σ(配比_i × 单煤指标_i)，其中 Ad/G/Y 按可加性处理；
        活惰比取加权和（无煤岩定量数据时退化为 0，由系数项决定影响）。

        TODO(标定): G、Y 的可加性在宽煤阶混配时不成立，需引入非线性修正
        （如 CBRI 的加权指数法），待 DOE 数据验证。
        """
        total = sum(ratios)
        if total <= 0:
            raise ValueError("配比之和必须为正")
        w = [r / total for r in ratios]

        def weighted(attr: str) -> float:
            return sum(getattr(c, attr) * wi for c, wi in zip(coals, w))

        active = sum((c.active_ratio or 0.0) * wi for c, wi in zip(coals, w))
        inert = sum((c.inert_ratio or 0.0) * wi for c, wi in zip(coals, w))
        return {
            "Ad": weighted("Ad"),
            "Vdaf": weighted("Vdaf"),
            "St_d": weighted("St_d"),
            "G": weighted("G"),
            "Y": weighted("Y"),
            "Rmax_mean": weighted("Rmax"),
            # 无煤岩定量数据时活惰比置 0，对应系数项不起作用
            "active_inert_ratio": active / inert if inert > 0 else 0.0,
        }

    # ------------------------------------------------------------------ #
    # 预测接口（与 ML 模型一致）
    # ------------------------------------------------------------------ #
    def predict(self, coals: List[SingleCoal], ratios: List[float]) -> Dict[str, float]:
        """预测焦炭质量。

        :param coals: 参与配煤的单种煤列表
        :param ratios: 对应配比（小数，允许未归一化，内部自动归一）
        :return: {"M25": ..., "M10": ..., "CSR": ..., "CRI": ...}
        """
        if len(coals) != len(ratios):
            raise ValueError("煤种列表与配比列表长度不一致")
        feats = self._blend_features(coals, ratios)
        result: Dict[str, float] = {}
        for target in TARGETS:
            coefs = self.coefficients[target]
            value = coefs.get("bias", 0.0) + sum(
                coefs.get(name, 0.0) * val for name, val in feats.items()
            )
            lo, hi = QUALITY_BOUNDS[target]
            result[target] = round(min(max(value, lo), hi), 2)
        return result

    def predict_from_records(
        self, coal_records: List[Dict[str, Any]], blend_ratio: Dict[str, float]
    ) -> Dict[str, float]:
        """适配方案 4.1.5 JSON 结构的便捷入口。

        :param coal_records: 元素形如 {"name": ..., "lab_data": {...}}
        :param blend_ratio:  {煤种名: 配比}
        """
        coals: List[SingleCoal] = []
        ratios: List[float] = []
        for rec in coal_records:
            name = rec["name"]
            if name not in blend_ratio or blend_ratio[name] <= 0:
                continue
            lab = rec.get("lab_data", {})
            coals.append(SingleCoal(name=name, **lab))
            ratios.append(blend_ratio[name])
        if not coals:
            raise ValueError("blend_ratio 与煤种列表无交集")
        return self.predict(coals, ratios)
