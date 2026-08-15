"""三阶段控制模式（方案 4.2.2）：Manual / AI_Shadow / AI_Auto。

- manual：完全人工控制，AI 不参与（烘炉期、异常工况）
- ai_shadow：AI 实时计算但不下发，仅记录推荐值并与人工操作值对比（试生产前3个月）
- ai_auto：AI 计算结果经安全钳位后自动下发 DCS，人工可一键切回手动

影子模式期积累的「AI推荐值 vs 人工操作值」对照数据，是 AI 上线评审的
核心依据，也是把人工调火经验蒸馏进模型的数据来源。
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from .mpc_controller import FurnaceState, MPCController, MPCOutput

logger = logging.getLogger(__name__)


class ControlMode(enum.Enum):
    """控制模式枚举（对齐方案 4.2.2 三阶段）。"""

    MANUAL = "manual"
    AI_SHADOW = "ai_shadow"
    AI_AUTO = "ai_auto"


@dataclass
class ShadowRecord:
    """影子模式对照记录：AI 推荐值 vs 人工实际操作值。"""

    timestamp: datetime
    ai_gas_flow: float
    ai_flue_draft: float
    human_gas_flow: float
    human_flue_draft: float
    predicted_temp_curve: List[float] = field(default_factory=list)

    @property
    def gas_flow_deviation(self) -> float:
        """AI 与人工的煤气流量偏差（m³/h）。"""
        return self.ai_gas_flow - self.human_gas_flow


class ShadowModeController:
    """三模式控制调度器：按当前模式决定 MPC 输出的去向。"""

    def __init__(
        self,
        mpc: MPCController,
        mode: ControlMode = ControlMode.MANUAL,
        dispatch: Optional[Callable[[MPCOutput], None]] = None,
        record_sink: Optional[Callable[[ShadowRecord], None]] = None,
    ):
        """
        :param mpc: MPC 控制器
        :param mode: 初始模式（默认 manual，绝不默认自动）
        :param dispatch: 设定值下发 DCS 的回调（仅 ai_auto 模式调用）；
            下发链路必须经 DCS 侧硬钳位（见 safety_limits 红线说明）
        :param record_sink: 影子记录落库回调（如写 PostgreSQL/Redis）
        """
        self.mpc = mpc
        self.mode = mode
        self.dispatch = dispatch
        self.record_sink = record_sink
        self.records: List[ShadowRecord] = []  # 内存暂存；record_sink 负责持久化

    # ------------------------------------------------------------------ #
    def set_mode(self, mode: ControlMode) -> None:
        """模式切换。

        ⚠️ 「一键切手动」为 DCS 侧硬切换，不经过本软件层（方案 4.2.6 红线）；
        本方法只同步 AI 侧状态，切入 manual 时立即停止一切下发。
        """
        logger.warning("控制模式切换: %s → %s", self.mode.value, mode.value)
        self.mode = mode

    # ------------------------------------------------------------------ #
    def on_control_cycle(self, state: FurnaceState,
                         human_gas_flow: Optional[float] = None,
                         human_flue_draft: Optional[float] = None) -> Optional[MPCOutput]:
        """每个控制周期（2 个交换周期）由调度层调用。

        :param state: 当前炉况快照
        :param human_gas_flow: 人工当前设定的煤气流量（影子模式记录用）
        :param human_flue_draft: 人工当前设定的吸力
        :return: MPC 输出（manual 模式返回 None）
        """
        if self.mode is ControlMode.MANUAL:
            return None

        output = self.mpc.step(state)

        if self.mode is ControlMode.AI_SHADOW:
            # 影子模式：只记录，不下发
            record = ShadowRecord(
                timestamp=datetime.now(),
                ai_gas_flow=output.gas_flow_setpoint,
                ai_flue_draft=output.flue_draft_setpoint,
                human_gas_flow=human_gas_flow if human_gas_flow is not None else state.current_gas_flow,
                human_flue_draft=human_flue_draft if human_flue_draft is not None else state.current_flue_draft,
                predicted_temp_curve=output.predicted_temp_curve,
            )
            self.records.append(record)
            if self.record_sink:
                self.record_sink(record)
            logger.info(
                "[影子模式] AI建议 煤气=%.0f 吸力=%.0f | 人工 煤气=%.0f 吸力=%.0f | 偏差 %.0f m³/h",
                record.ai_gas_flow, record.ai_flue_draft,
                record.human_gas_flow, record.human_flue_draft,
                record.gas_flow_deviation,
            )
            return output

        # ai_auto：钳位后的设定值下发 DCS（DCS 侧硬钳位为最终屏障）
        if self.dispatch is None:
            raise RuntimeError("ai_auto 模式必须配置 dispatch 下发回调")
        self.dispatch(output)
        logger.info("[自动模式] 设定值已下发: 煤气=%.0f m³/h 吸力=%.0f Pa%s",
                    output.gas_flow_setpoint, output.flue_draft_setpoint,
                    "（触发钳位）" if output.clamped else "")
        return output

    # ------------------------------------------------------------------ #
    def shadow_report(self) -> dict:
        """影子模式统计报告（AI 上线评审输入）。

        TODO(评审): 增加偏差分布、分班次对比、与 K均/K安 系数的关联分析。
        """
        if not self.records:
            return {"n_records": 0}
        deviations = [abs(r.gas_flow_deviation) for r in self.records]
        return {
            "n_records": len(self.records),
            "mean_abs_gas_flow_deviation": round(sum(deviations) / len(deviations), 1),
            "max_abs_gas_flow_deviation": round(max(deviations), 1),
        }
