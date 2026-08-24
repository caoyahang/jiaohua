"""MPC 模型预测控制器（方案 4.2.4 四步骤）。

步骤1 状态预估：LSTM 温度预测器 → 未来 30min 温度曲线
步骤2 优化求解：PSO 求最优煤气流量/分烟道吸力（每 2 个交换周期执行一次）
步骤3 约束检查：safety_limits 三通道设定值钳位（DCS 侧另有硬钳位兜底）
步骤4 反馈校正：实际温度 vs 预测温度 → 误差补偿 → 下次预测修正
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from sko.PSO import PSO

from . import safety_limits
from .lstm_model import TemperaturePredictor

logger = logging.getLogger(__name__)


@dataclass
class FurnaceState:
    """焦炉当前状态快照（由数据采集层填充）。"""

    history_60min: np.ndarray          # (60, n_features) 过去60min序列
    target_temp: float = 1250.0        # 标准温度目标 ℃
    current_gas_flow: float = 8000.0   # 当前煤气流量 m³/h
    current_flue_draft: float = 200.0  # 当前分烟道吸力 Pa
    current_collector_pressure: float = 100.0  # 当前集气管压力 Pa


@dataclass
class MPCOutput:
    """MPC 单步输出（步骤3下发内容，对齐方案 4.2.4）。"""

    gas_flow_setpoint: float
    flue_draft_setpoint: float
    air_excess_suggestion: float       # 空气过剩系数建议值（仅供调火工参考，不下发）
    predicted_temp_curve: List[float]  # 最优控制量下的预测温度曲线
    clamped: bool = False              # 是否触发了安全钳位


@dataclass
class FeedbackCorrector:
    """步骤4：反馈校正器（指数滑动平均误差补偿）。"""

    alpha: float = 0.3                 # 补偿更新率
    bias: float = 0.0                  # 当前累计预测偏差 ℃

    def update(self, actual_temp: float, predicted_temp: float) -> None:
        """实测与预测对比，更新偏差补偿。"""
        self.bias = self.alpha * (actual_temp - predicted_temp) + (1 - self.alpha) * self.bias

    def correct(self, predicted_curve: np.ndarray) -> np.ndarray:
        """对预测曲线叠加偏差补偿。"""
        return predicted_curve + self.bias


class MPCController:
    """焦炉加热 MPC 控制器。"""

    def __init__(
        self,
        temp_predictor: TemperaturePredictor,
        horizon_steps: int = 30,
        gas_cost_weight: float = 0.001,  # λ：煤气消耗惩罚权重（方案 4.2.4 目标函数）
        pso_pop: int = 30,
        pso_max_iter: int = 100,
        seed: int = 42,
    ):
        self.predictor = temp_predictor
        self.horizon = horizon_steps
        self.gas_cost_weight = gas_cost_weight
        self.pso_pop = pso_pop
        self.pso_max_iter = pso_max_iter
        self.seed = seed
        self.corrector = FeedbackCorrector()

    # ------------------------------------------------------------------ #
    # 主入口：单步 MPC 求解
    # ------------------------------------------------------------------ #
    def step(self, state: FurnaceState) -> MPCOutput:
        """执行一次完整 MPC 循环（步骤1→2→3；步骤4由 feedback_update 驱动）。"""
        # 步骤2：PSO 求解最优 (煤气流量, 分烟道吸力)
        best_u, pred_curve = self._solve(state)

        # 步骤3：约束检查 —— AI 侧软件钳位（DCS 硬钳位为最终屏障，见 safety_limits）
        raw_gas, raw_draft = float(best_u[0]), float(best_u[1])
        clamped = safety_limits.clamp_all(
            gas_flow=raw_gas, flue_draft=raw_draft,
            collector_pressure=state.current_collector_pressure,  # AI 不主动调集气管，保持当前值
            current_gas_flow=state.current_gas_flow,
            current_flue_draft=state.current_flue_draft,
            current_collector_pressure=state.current_collector_pressure,
        )
        was_clamped = (
            clamped["gas_flow"] != round(raw_gas, 2)
            or clamped["flue_draft"] != round(raw_draft, 2)
        )
        # 记录首步预测值，供步骤4反馈校正（实测 vs 预测对比）
        self._last_predicted_first_step = float(pred_curve[0])
        # TODO(空燃比): 空气过剩系数建议值应由残氧目标反推，当前占位为经验值 1.2
        return MPCOutput(
            gas_flow_setpoint=clamped["gas_flow"],
            flue_draft_setpoint=clamped["flue_draft"],
            air_excess_suggestion=1.2,
            predicted_temp_curve=[round(float(t), 1) for t in pred_curve],
            clamped=was_clamped,
        )

    # ------------------------------------------------------------------ #
    # 步骤1+2：状态预估 + PSO 优化求解
    # ------------------------------------------------------------------ #
    def _solve(self, state: FurnaceState) -> tuple[np.ndarray, np.ndarray]:
        """PSO 最小化：Σ(预测温度−目标温度)² + λ·煤气消耗量。

        决策变量：[煤气流量 m³/h, 分烟道吸力 Pa]
        温度对控制量的响应：LSTM 以「候选控制量替换历史末端控制量」的方式做
        条件预测（骨架近似）。

        TODO(模型): 严格 MPC 应让 LSTM 学习 (控制量→温度) 的动态响应并把
        候选序列外推 30 步作为输入；当前用末端替换近似，待模型迭代。
        """
        limits = safety_limits

        def simulate_temp_curve(u: np.ndarray) -> np.ndarray:
            history = state.history_60min.copy()
            # 用候选控制量替换最近若干步的煤气流量/吸力列（条件预测近似）
            history[-5:, 1] = u[0]   # gas_flow 列
            history[-5:, 2] = u[1]   # flue_draft 列
            curve = self.predictor.predict_next_30min(history)
            return self.corrector.correct(curve)

        def objective(u: np.ndarray) -> float:
            curve = simulate_temp_curve(u)
            tracking = float(np.sum((curve - state.target_temp) ** 2))
            gas_penalty = self.gas_cost_weight * u[0]
            # 温度软约束（方案 4.2.4：温度上下限）
            bound_violation = (
                np.maximum(curve - safety_limits.TEMP_TARGET_MAX, 0).sum()
                + np.maximum(safety_limits.TEMP_TARGET_MIN - curve, 0).sum()
            )
            return tracking + gas_penalty + float(bound_violation) * 100.0

        # scikit-opt 0.6.x 的 PSO 不再接收 seed 参数，用全局随机种子保证可复现
        np.random.seed(self.seed)
        pso = PSO(
            func=objective,
            n_dim=2,
            pop=self.pso_pop,
            max_iter=self.pso_max_iter,
            lb=[limits.GAS_FLOW_LIMIT.abs_min, limits.FLUE_DRAFT_LIMIT.abs_min],
            ub=[limits.GAS_FLOW_LIMIT.abs_max, limits.FLUE_DRAFT_LIMIT.abs_max],
            w=0.8, c1=0.5, c2=0.5,
        )
        pso.run()
        best_u = np.asarray(pso.gbest_x, dtype=float)
        return best_u, simulate_temp_curve(best_u)

    # ------------------------------------------------------------------ #
    # 步骤4：反馈校正（每个交换周期由调度层调用）
    # ------------------------------------------------------------------ #
    def feedback_update(self, actual_temp: float) -> None:
        """实测温度回来后的反馈校正（方案 4.2.4 步骤4）。"""
        if not hasattr(self, "_last_predicted_first_step"):
            return
        self.corrector.update(actual_temp, self._last_predicted_first_step)
        logger.debug("反馈校正：当前偏差补偿 %.2f℃", self.corrector.bias)
