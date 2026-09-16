"""安全视觉AI（方案 4.4.1）：YOLOv8 训练 / 帧推理 / 告警引擎。

识别场景：安全帽/反光衣、烟火、违规闯入（骨干三场景，V1.1 MVP 范围）；
煤气泄漏红外、表计读数、焦饼成熟度为后续扩展。

ultralytics 相关对象按 PEP 562 懒加载（inference 依赖 ultralytics），保证
未安装 ultralytics 时仍可独立导入 alarm_engine 等轻量模块（总纲§1）。
"""

from __future__ import annotations

from .alarm_engine import AlarmEngine, AlarmEvent

__all__ = ["VisionInference", "AlarmEngine", "AlarmEvent"]


def __getattr__(name: str):
    """按需加载 ultralytics 相关推理模块（方案§6.1）。"""
    if name == "VisionInference":
        from .inference import VisionInference

        return VisionInference
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
