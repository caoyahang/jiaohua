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
