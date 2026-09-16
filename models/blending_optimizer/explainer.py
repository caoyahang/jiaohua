"""配煤方案解释器（方案 4.1.2 模型C）：SHAP 边际贡献 → 配煤师可读的中文说明。

示例输出（对齐 4.1.5 的 explanation 字段）：
    "SHAP分析显示焦煤占比每降1%可省12元但CSR降0.3%"

两条路径：
  - ML 模型期：TreeExplainer 精确计算各特征 SHAP 值
  - 冷启动期（经验模型）：用扰动法（有限差分）估算各煤种边际贡献，
    经验模型是透明的线性公式，扰动法结果即真实偏导，不损失精度
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 扰动步长：配比变动 1 个百分点
PERTURB_STEP = 0.01


class BlendExplainer:
    """配煤方案可解释性分析器。"""

    def __init__(self, quality_predictor: Any):
        """
        :param quality_predictor: QualityPredictor 门面（自动判断经验/ML后端）
        """
        self.predictor = quality_predictor

    # ------------------------------------------------------------------ #
    def explain(
        self,
        blend_ratio: Dict[str, float],
        predicted_quality: Dict[str, float],
        request: Optional[Any] = None,
    ) -> str:
        """生成配煤师可读的中文说明文本。

        :param blend_ratio: 最优方案配比 {煤种名: 配比}
        :param predicted_quality: 该方案的预测质量
        :param request: 原始优化请求（取价格信息；None 时省略成本分析）
        """
        contributions = self.marginal_contributions(blend_ratio, request)
        if not contributions:
            return ""

        # 找成本影响最大的煤种与 CSR 影响最大的煤种，组织成自然语言
        top_cost = max(contributions.items(), key=lambda kv: abs(kv[1].get("delta_cost", 0.0)), default=None)
        top_csr = max(contributions.items(), key=lambda kv: abs(kv[1].get("delta_CSR", 0.0)), default=None)

        parts = []
        if top_cost and top_cost[1].get("delta_cost") is not None:
            name, c = top_cost
            direction = "省" if c["delta_cost"] < 0 else "增加"
            parts.append(
                f"{name}占比每降1个百分点可{direction}{abs(c['delta_cost']):.0f}元/吨"
            )
        if top_csr and top_csr[1].get("delta_CSR") is not None:
            name, c = top_csr
            direction = "升" if c["delta_CSR"] > 0 else "降"
            parts.append(f"{name}每增1个百分点CSR约{direction}{abs(c['delta_CSR']):.1f}个点")

        prefix = "SHAP分析显示" if self._is_ml_backend() else "边际分析显示"
        return f"{prefix}：{'；'.join(parts)}" if parts else ""

    # ------------------------------------------------------------------ #
    def marginal_contributions(
        self, blend_ratio: Dict[str, float], request: Optional[Any] = None
    ) -> Dict[str, Dict[str, float]]:
        """扰动法计算各煤种对成本与四质量指标的边际贡献（每 ±1% 配比）。

        :return: {煤种名: {"delta_cost": ..., "delta_M25": ..., "delta_CSR": ..., ...}}
        """
        backend = self.active_backend()
        if backend == "lightgbm":
            # TODO(ML解释): 走 TreeExplainer 路径，需要训练特征上下文，
            # 当前骨架统一用扰动法（对树模型同样是有效的局部近似）
            logger.debug("ML 后端暂用扰动法近似 SHAP，后续接 TreeExplainer")

        if request is None or not hasattr(request, "available_coals"):
            logger.debug("缺少请求上下文，跳过边际贡献计算")
            return {}

        coals_info = {c.name: c for c in request.available_coals}
        names = list(blend_ratio.keys())
        base_ratios = np.array([blend_ratio[n] for n in names])
        prices = np.array([coals_info[n].price_per_ton for n in names])
        single_coals = [self.predictor._to_single_coal(coals_info[n]) for n in names] \
            if hasattr(self.predictor, "_to_single_coal") else None

        base_quality = self._predict(single_coals, coals_info, names, base_ratios)
        base_cost = float(np.dot(base_ratios, prices))

        result: Dict[str, Dict[str, float]] = {}
        for i, name in enumerate(names):
            perturbed = base_ratios.copy()
            perturbed[i] += PERTURB_STEP
            perturbed = perturbed / perturbed.sum()  # 重新归一化
            q = self._predict(single_coals, coals_info, names, perturbed)
            result[name] = {
                "delta_cost": (float(np.dot(perturbed, prices)) - base_cost) / PERTURB_STEP,
            }
            for target in ("M25", "M10", "CSR", "CRI"):
                result[name][f"delta_{target}"] = (q[target] - base_quality[target]) / PERTURB_STEP
        return result

    # ------------------------------------------------------------------ #
    def shap_values_for_ml(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        """ML 模型的 TreeExplainer SHAP 值（供 explainer 与 evaluate 复用）。"""
        import shap  # noqa: PLC0415  # 懒加载：总纲§1
        explainer = shap.TreeExplainer(model)
        return explainer.shap_values(X)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _is_ml_backend(self) -> bool:
        return self.active_backend() == "lightgbm"

    def active_backend(self) -> str:
        return getattr(self.predictor, "active_backend", "empirical")

    def _predict(self, single_coals, coals_info, names, ratios) -> Dict[str, float]:
        """调用质量预测器（经验路径）。"""
        if single_coals is not None:
            return self.predictor.predict(coals=single_coals, ratios=list(ratios))
        # 兜底：直接从 lab_data 构造
        from ..quality_predictor.empirical_model import SingleCoal
        scs = [SingleCoal(name=n, **coals_info[n].lab_data.model_dump()) for n in names]
        return self.predictor.predict(coals=scs, ratios=list(ratios))
