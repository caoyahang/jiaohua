"""智能配煤契约（方案§4.1.5 输入输出规范、§4.1.7 化验回流）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TargetQuality(BaseModel):
    """目标焦炭质量指标。"""

    M25_min: float = Field(90.0, description="抗碎强度M25下限 %")
    M10_max: float = Field(6.5, description="耐磨强度M10上限 %")
    CSR_min: float = Field(65.0, description="反应后强度CSR下限 %")
    CRI_max: float = Field(25.0, description="反应性CRI上限 %")


class CoalInfo(BaseModel):
    """可用煤种信息（含库存约束与化验指标）。"""

    coal_id: int
    name: str
    stock_tons: float = Field(..., gt=0, description="库存量 吨")
    price_per_ton: float = Field(..., gt=0, description="单价 元/吨")
    min_ratio: float = Field(0.0, ge=0, le=1, description="配比下限（工艺约束）")
    max_ratio: float = Field(1.0, ge=0, le=1, description="配比上限（工艺约束）")
    lab_data: dict = Field(default_factory=dict, description="化验指标：Ad/Vdaf/St_d/G/Y/Rmax等")


class OptimizeRequest(BaseModel):
    """配煤优化请求（4.1.5输入JSON）。"""

    target_quality: TargetQuality
    available_coals: list[CoalInfo] = Field(..., min_length=2)
    max_cost_per_ton: float = Field(1500.0, gt=0)
    priority: str = Field("cost", pattern="^(cost|quality|balanced)$")


class LabFeedback(BaseModel):
    """化验结果回流（4.1.7增量学习入口）。"""

    batch_no: str = Field(..., description="配煤批次号")
    actual_quality: dict = Field(..., description="实测焦炭质量：M25/M10/CSR/CRI")
