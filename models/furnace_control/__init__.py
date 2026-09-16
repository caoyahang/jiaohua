"""焦炉AI智能加热控制（方案§4.2）：LSTM + MPC + 安全红线。

安全限值是轻量模块，允许直接导入；Torch/scikit-opt 相关对象按 PEP 562
懒加载，保证未安装重依赖时仍可独立导入并测试安全红线。
"""

from __future__ import annotations

from .safety_limits import SafetyLimitError, clamp_setpoint

__all__ = [
    "clamp_setpoint", "SafetyLimitError",
    "ControlMode", "ShadowModeController",
    "MPCController", "TemperatureLSTM",
]


def __getattr__(name: str):
    """按需加载 Torch/scikit-opt 相关控制模型（方案§6.1）。"""
    if name in ("ControlMode", "ShadowModeController"):
        from . import shadow_mode

        return getattr(shadow_mode, name)
    if name == "MPCController":
        from .mpc_controller import MPCController

        return MPCController
    if name == "TemperatureLSTM":
        from .lstm_model import TemperatureLSTM

        return TemperatureLSTM
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
