"""焦炉加热控制契约（方案§4.2）。"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ControlModeRequest(BaseModel):
    """AI控制模式软切换请求（方案§4.2.2/§4.2.6）。"""

    furnace_id: int = Field(..., description="焦炉编号")
    mode: str = Field(..., pattern="^(shadow|auto)$", description="仅允许影子/自动软切换")
    operator: str = Field(..., min_length=1, description="操作人工号/姓名")
    reviewer: str = Field(..., min_length=1, description="复核人工号/姓名")
    reason: str = Field(..., min_length=1, description="切换原因")
    confirm: bool = Field(..., description="复核人现场确认后必须为 true")

    @model_validator(mode="after")
    def validate_dual_confirmation(self) -> "ControlModeRequest":
        """强制双人确认；手动模式只能由 DCS 硬切换。"""
        if self.operator == self.reviewer:
            raise ValueError("复核人不得与操作人相同")
        if not self.confirm:
            raise ValueError("控制模式软切换必须双人确认")
        return self


class ControlModeResponse(BaseModel):
    """POST /furnace/control-mode 响应（方案§4.2.2）。"""

    furnace_id: int = Field(..., description="焦炉编号")
    mode: str = Field(..., description="切换后的控制模式")
    status: str = Field(..., description="状态：ok")


class KShiftRecord(BaseModel):
    """单班次热工/推焦 K 系数（方案§4.2.6 统一考核口径）。

    字段名与 `docs/API文档.md` §GET /furnace/k-coefficients 契约一致；
    K3 恒等于 K1×K2（红线恒等式，见 data/pipeline/k_coefficients.py）。
    """

    furnace_id: int = Field(..., description="焦炉编号")
    shift_date: str = Field(..., description="班次日期 YYYY-MM-DD")
    shift: str = Field(..., description="班次：早班/中班/晚班")
    k_uniform: float = Field(..., description="K均：直行温度均匀系数（目标≥0.90）")
    k_stable: float = Field(..., description="K安：直行温度安定系数")
    k1: float = Field(..., description="K1：推焦计划系数")
    k2: float = Field(..., description="K2：推焦执行系数")
    k3: float = Field(..., description="K3：推焦总系数，恒等于 K1×K2（目标≥0.95）")


class KCoefficientsResponse(BaseModel):
    """GET /furnace/k-coefficients 响应（班次记录列表，供趋势展示）。"""

    records: list[KShiftRecord]
