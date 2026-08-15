"""V1.1 安全红线：AI 下发设定值的上下限与变化速率钳位（方案 4.2.6）。

⚠️ 安全联锁硬隔离（红线，已同步写入第九章 DCS 招标条款）：
  - 集气管压力高限、煤气压力低限、烟道吸力低限等安全联锁【永远走 DCS 硬联锁回路】，
    AI 通道物理上无权触碰；本模块的钳位只是 AI 侧的软件自律，不是安全屏障。
  - AI 只输出设定值（setpoint）；设定值上下限与变化速率必须在【DCS 侧硬钳位】，
    不依赖本模块 —— 本模块失效（如 AI 服务被绕过）时 DCS 钳位依然生效。
  - AI 服务宕机/网络中断时，DCS 自动保持【最后有效设定值】并报警，不依赖 AI 心跳。
  - 「一键切手动」为硬切换，不经过 AI 系统软件层。

本模块职责：在 AI 侧提前把设定值收敛到安全包线内，避免频繁触发 DCS 硬钳位
造成的设定值抖动；同时输出钳位记录供审计。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class SafetyLimitError(ValueError):
    """设定值超出安全包线且无法钳位（如当前值本身已越限）时抛出。"""


@dataclass(frozen=True)
class SetpointLimit:
    """单通道设定值安全包线。

    常量值取自焦炉热工通用规程的典型区间，
    TODO(标定): 必须按本厂炉型（炭化室高度/结焦时间/煤气种类）与 DCS 硬钳位值
    逐项核对 —— AI 侧包线应严格窄于或等于 DCS 硬钳位包线。
    """

    name: str            # 通道名
    unit: str            # 单位
    abs_min: float       # 设定值绝对下限
    abs_max: float       # 设定值绝对上限
    max_rate: float      # 单次调整最大变化量（对应一个控制周期）
    current: float = 0.0  # 当前有效设定值（速率钳位的基准）


# --------------------------------------------------------------------------- #
# 安全包线常量（典型值，待按本厂 DCS 组态核对）
# --------------------------------------------------------------------------- #
GAS_FLOW_LIMIT = SetpointLimit(
    name="煤气流量", unit="m³/h",
    abs_min=3000.0, abs_max=15000.0,
    max_rate=300.0,  # 每控制周期(2个交换周期)最多调 ±300 m³/h
)
FLUE_DRAFT_LIMIT = SetpointLimit(
    name="分烟道吸力", unit="Pa",
    abs_min=80.0, abs_max=350.0,
    max_rate=10.0,
)
COLLECTOR_PRESSURE_LIMIT = SetpointLimit(
    name="集气管压力", unit="Pa",
    abs_min=60.0, abs_max=160.0,
    max_rate=5.0,
    # 注意：集气管压力高限联锁走 DCS 硬回路，此处仅为 AI setpoint 自律包线
)
# 火道温度软约束（MPC 目标函数用，非 setpoint 钳位）
TEMP_TARGET_MIN = 1150.0   # ℃
TEMP_TARGET_MAX = 1350.0   # ℃


def clamp_setpoint(value: float, limit: SetpointLimit) -> float:
    """把 AI 计算的设定值钳位到安全包线内（绝对上下限 + 变化速率）。

    :param value: AI 计算的目标设定值
    :param limit: 该通道的安全包线（current 字段为当前有效设定值）
    :return: 钳位后的设定值
    :raises SafetyLimitError: 当前设定值本身已越出绝对包线（工况异常，AI 不应继续输出）
    """
    if not (limit.abs_min <= limit.current <= limit.abs_max):
        raise SafetyLimitError(
            f"{limit.name}当前值 {limit.current}{limit.unit} 已越出安全包线 "
            f"[{limit.abs_min}, {limit.abs_max}]，AI 停止输出，等待人工/DCS 处置"
        )

    clamped = min(max(value, limit.abs_min), limit.abs_max)
    delta = clamped - limit.current
    if abs(delta) > limit.max_rate:
        clamped = limit.current + limit.max_rate * (1 if delta > 0 else -1)
        logger.info("%s 设定值变化速率超限，钳位为 %.2f%s", limit.name, clamped, limit.unit)

    if clamped != value:
        logger.info("%s 设定值 %.2f → 钳位后 %.2f%s", limit.name, value, clamped, limit.unit)
    return round(clamped, 2)


def clamp_all(
    gas_flow: float, flue_draft: float, collector_pressure: float,
    current_gas_flow: float, current_flue_draft: float, current_collector_pressure: float,
) -> dict:
    """对 MPC 输出的三通道设定值统一钳位。

    :return: {"gas_flow": ..., "flue_draft": ..., "collector_pressure": ...}
    """
    return {
        "gas_flow": clamp_setpoint(gas_flow, SetpointLimit(
            **{**GAS_FLOW_LIMIT.__dict__, "current": current_gas_flow})),
        "flue_draft": clamp_setpoint(flue_draft, SetpointLimit(
            **{**FLUE_DRAFT_LIMIT.__dict__, "current": current_flue_draft})),
        "collector_pressure": clamp_setpoint(collector_pressure, SetpointLimit(
            **{**COLLECTOR_PRESSURE_LIMIT.__dict__, "current": current_collector_pressure})),
    }
