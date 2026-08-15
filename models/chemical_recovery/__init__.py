"""化产回收AI优化（方案 4.6，二期，V1.1 新增）。

接入条件：化产系统 OPC UA 数据积累 ≥3 个月后启动（接口见方案 3.2.1）。
当前仅为骨架：定义四个优化场景类与方法签名，核心逻辑全部 TODO。
"""

from .optimizer import (
    BenzolScrubberOptimizer,
    SaturatorOptimizer,
    GasCoolingOptimizer,
    DesulfurizationOptimizer,
)

__all__ = [
    "BenzolScrubberOptimizer", "SaturatorOptimizer",
    "GasCoolingOptimizer", "DesulfurizationOptimizer",
]
