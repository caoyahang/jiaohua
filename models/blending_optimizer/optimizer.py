"""配煤成本优化器（方案 4.1.2 模型B）：scikit-opt 遗传算法寻优。

目标函数：min 吨煤成本（+ 约束罚项），调用质量预测模型（模型A）作为适应度
评估的一部分；按 priority 输出三套方案：cost_optimal / quality_stable / balanced。

输入输出以 pydantic 模型对齐方案 4.1.5 的 JSON 规范。
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Literal, Optional

import numpy as np
from pydantic import BaseModel, Field
from sko.GA import GA

from ..quality_predictor.empirical_model import SingleCoal
from ..quality_predictor.predict import QualityPredictor
from . import constraints
from .explainer import BlendExplainer

logger = logging.getLogger(__name__)

MODEL_VERSION = "v1.0-skeleton"

# 三套方案的（成本权重, 质量罚权重）配比：cost 重成本，quality 重质量余量，balanced 折中
PRIORITY_PROFILES: Dict[str, Dict[str, float]] = {
    "cost_optimal": {"cost_weight": 1.0, "quality_margin_weight": 0.0},
    "quality_stable": {"cost_weight": 0.6, "quality_margin_weight": 0.4},
    "balanced": {"cost_weight": 0.8, "quality_margin_weight": 0.2},
}


# --------------------------------------------------------------------------- #
# 输入输出模型（对齐方案 4.1.5 JSON）
# --------------------------------------------------------------------------- #
class CoalLabData(BaseModel):
    Ad: float = Field(..., description="灰分(干基)%")
    Vdaf: float = Field(..., description="挥发分(干燥无灰基)%")
    St_d: float = Field(..., description="全硫(干基)%")
    G: float = Field(..., description="粘结指数")
    Y: float = Field(..., description="胶质层厚度mm")
    Rmax: float = Field(..., description="镜质组平均最大反射率%")


class AvailableCoal(BaseModel):
    coal_id: int
    name: str
    stock_tons: float
    price_per_ton: float
    min_ratio: float = 0.0
    max_ratio: float = 1.0
    lab_data: CoalLabData


class OptimizeRequest(BaseModel):
    """配煤优化请求（对应 4.1.5 输入 JSON）。"""

    target_quality: constraints.QualityTarget = Field(default_factory=constraints.QualityTarget)
    available_coals: List[AvailableCoal]
    max_cost_per_ton: float = 1500.0
    priority: Literal["cost", "quality", "balanced"] = "cost"
    daily_consumption_tons: float = Field(default=2000.0, description="日耗煤量(吨)，用于库存天数约束")


class BlendSolution(BaseModel):
    """单套配煤方案（对应 4.1.5 输出 JSON 的 solutions 元素）。"""

    type: Literal["cost_optimal", "quality_stable", "balanced"]
    blend_ratio: Dict[str, float]
    estimated_cost: float
    predicted_quality: Dict[str, float]
    confidence: float
    explanation: str = ""


class OptimizeResponse(BaseModel):
    solutions: List[BlendSolution]
    model_version: str = MODEL_VERSION
    compute_time_ms: int = 0


# --------------------------------------------------------------------------- #
# 优化器
# --------------------------------------------------------------------------- #
class BlendingOptimizer:
    """遗传算法配煤优化器。"""

    def __init__(
        self,
        quality_predictor: QualityPredictor,
        explainer: Optional[BlendExplainer] = None,
        ga_size_pop: int = 50,
        ga_max_iter: int = 200,
        seed: int = 42,
    ):
        """
        :param quality_predictor: 质量预测模型（模型A），作为适应度函数的"模拟器"
        :param explainer: SHAP 解释器（模型C）；None 时 explanation 留占位
        :param ga_size_pop: GA 种群规模
        :param ga_max_iter: GA 迭代代数
        """
        self.predictor = quality_predictor
        self.explainer = explainer
        self.ga_size_pop = ga_size_pop
        self.ga_max_iter = ga_max_iter
        self.seed = seed

    # ------------------------------------------------------------------ #
    def optimize(self, request: OptimizeRequest) -> OptimizeResponse:
        """求解三套配煤方案。

        对 cost/quality/balanced 三种 priority 各跑一次 GA（质量权重不同），
        汇总为 OptimizeResponse。
        """
        t0 = time.perf_counter()
        solutions: List[BlendSolution] = []
        for sol_type, profile in PRIORITY_PROFILES.items():
            try:
                sol = self._solve_single(request, sol_type, profile)
                solutions.append(sol)
            except Exception:
                logger.exception("方案 %s 求解失败，跳过", sol_type)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        if not solutions:
            raise RuntimeError("三套方案均求解失败，请检查约束是否过紧或库存不足")
        return OptimizeResponse(solutions=solutions, compute_time_ms=elapsed_ms)

    # ------------------------------------------------------------------ #
    def _solve_single(
        self, request: OptimizeRequest, sol_type: str, profile: Dict[str, float]
    ) -> BlendSolution:
        """单套方案求解：GA 最小化 [成本×cost_weight − 质量余量×quality_margin_weight + 罚项]。"""
        coals = request.available_coals
        n = len(coals)
        lb = np.array([c.min_ratio for c in coals])
        ub = np.array([c.max_ratio for c in coals])
        prices = np.array([c.price_per_ton for c in coals])
        stocks = [c.stock_tons for c in coals]

        single_coals = [
            SingleCoal(name=c.name, **c.lab_data.model_dump()) for c in coals
        ]

        def objective(x: np.ndarray) -> float:
            ratios = self._normalize(x)
            cost = float(np.dot(ratios, prices))
            quality = self.predictor.predict(
                coals=single_coals, ratios=ratios.tolist()
            )
            pen = constraints.penalty(
                ratios.tolist(), lb.tolist(), ub.tolist(), stocks,
                request.daily_consumption_tons, quality, request.target_quality,
            )
            # 质量余量：CSR 越高、CRI/M10 越低余量越大，quality_stable 方案追求余量最大化
            margin = (
                quality["CSR"] - request.target_quality.CSR_min
                + request.target_quality.CRI_max - quality["CRI"]
                + request.target_quality.M10_max - quality["M10"]
            )
            value = (
                profile["cost_weight"] * cost
                - profile["quality_margin_weight"] * margin * 10.0
                + pen
            )
            if cost > request.max_cost_per_ton:
                value += (cost - request.max_cost_per_ton) * constraints.PENALTY_WEIGHT * 0.1
            return value

        # scikit-opt 0.6.x 的 GA 不再接收 seed 参数，用全局随机种子保证可复现
        np.random.seed(self.seed)
        ga = GA(
            func=objective,
            n_dim=n,
            size_pop=self.ga_size_pop,
            max_iter=self.ga_max_iter,
            prob_mut=0.01,
            lb=lb.tolist(),
            ub=ub.tolist(),
            precision=1e-4,
        )
        best_x, _ = ga.run()
        # GA 个体经归一化后仍可能越出上下限（缩放所致），输出前投影回有界单纯形
        ratios = self._project_to_bounds(best_x, lb, ub)

        blend_ratio = {c.name: round(float(r), 4) for c, r in zip(coals, ratios) if r > 1e-4}
        quality = self.predictor.predict(coals=single_coals, ratios=ratios.tolist())
        cost = float(np.dot(ratios, prices))

        # 硬校验兜底：GA + 罚函数是软约束，输出前再过一遍硬校验
        violations = constraints.validate(
            blend_ratio,
            {c.name: c.min_ratio for c in coals},
            {c.name: c.max_ratio for c in coals},
            quality, request.target_quality,
        )
        confidence = 1.0 if not violations else max(0.3, 1.0 - 0.15 * len(violations))
        if violations:
            logger.warning("方案 %s 存在约束风险: %s", sol_type, violations)

        explanation = ""
        if self.explainer:
            explanation = self.explainer.explain(blend_ratio, quality, request)

        return BlendSolution(
            type=sol_type, blend_ratio=blend_ratio,
            estimated_cost=round(cost, 1),
            predicted_quality=quality,
            confidence=round(confidence, 2),
            explanation=explanation,
        )

    @staticmethod
    def _normalize(x: np.ndarray) -> np.ndarray:
        """归一化配比使其和为 1（GA 个体不保证 Σ=1）。"""
        x = np.clip(np.asarray(x, dtype=float), 0.0, None)
        total = x.sum()
        return x / total if total > 0 else np.full_like(x, 1.0 / len(x))

    @staticmethod
    def _project_to_bounds(x: np.ndarray, lb: np.ndarray, ub: np.ndarray) -> np.ndarray:
        """把配比投影到有界单纯形 {lb ≤ r ≤ ub 且 Σr = 1}（水位法迭代）。

        归一化缩放会破坏 GA 保证的逐维上下限，最终方案输出前必须过此投影，
        保证硬校验（constraints.validate）不会因配比越界报警。
        前置条件：Σlb ≤ 1 ≤ Σub（路由层已做可行性检查）。
        """
        r = np.clip(np.asarray(x, dtype=float), lb, ub)
        for _ in range(len(r) * 10):  # 每轮至少钉住一个变量，有限步内收敛
            deficit = 1.0 - r.sum()
            if abs(deficit) < 1e-12:
                break
            if deficit > 0:
                room = np.where(r < ub - 1e-12, ub - r, 0.0)
            else:
                room = np.where(r > lb + 1e-12, r - lb, 0.0)
            total_room = room.sum()
            if total_room <= 0:
                break  # 无可行域，理论不可达（前置检查已拦截）
            r = np.clip(r + np.sign(deficit) * room / total_room * abs(deficit), lb, ub)
        return r
