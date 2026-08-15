"""安全视觉AI（方案 4.4.1）：YOLOv8 训练 / 帧推理 / 告警引擎。

识别场景：安全帽/反光衣、烟火、违规闯入（骨干三场景，V1.1 MVP 范围）；
煤气泄漏红外、表计读数、焦饼成熟度为后续扩展。
"""

from .inference import VisionInference
from .alarm_engine import AlarmEngine, AlarmEvent

__all__ = ["VisionInference", "AlarmEngine", "AlarmEvent"]
