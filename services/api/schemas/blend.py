"""智能配煤契约（方案§4.1.5 输入输出规范、§4.1.7 化验回流）。"""

from __future__ import annotations

from datetime import date, datetime

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


class BlendSolution(BaseModel):
    """单套配煤方案（方案§4.1.5 输出规范）。

    字段与 models/blending_optimizer/optimizer.py 的 BlendSolution 对齐，
    此处为服务层契约（不依赖 scikit-opt 重依赖，可被路由轻量引用）。
    """

    type: str = Field(..., description="方案类型：cost_optimal/quality_stable/balanced")
    blend_ratio: dict[str, float] = Field(..., description="各煤种配比（和为1）")
    estimated_cost: float = Field(..., description="预估吨煤成本 元/吨")
    predicted_quality: dict[str, float] = Field(..., description="预测质量：M25/M10/CSR/CRI")
    confidence: float = Field(..., description="置信度 0~1")
    explanation: str = Field("", description="SHAP/边际贡献中文解释")


class OptimizeResponse(BaseModel):
    """配煤优化响应（方案§4.1.5）。"""

    solutions: list[BlendSolution] = Field(..., description="三套方案")
    model_version: str = Field(..., description="模型版本")
    compute_time_ms: int = Field(0, description="求解耗时 毫秒")


class RecipeRow(BaseModel):
    """历史配煤方案行（blend_recipe 表，方案§3.4.1）。"""

    id: int
    batch_no: str
    furnace_id: int
    production_date: date | None = None
    total_coal_tons: float | None = None
    estimated_cost_per_ton: float | None = None
    actual_cost_per_ton: float | None = None
    ai_generated: bool = False
    operator_id: int | None = None
    approved_by: int | None = None
    created_at: datetime | None = None
    notes: str | None = None


class RecipeListResponse(BaseModel):
    """GET /blend/recipes 响应。"""

    recipes: list[RecipeRow]
