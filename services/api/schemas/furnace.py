"""焦炉加热控制契约（方案§4.2）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ControlModeRequest(BaseModel):
    """控制模式切换请求。"""

    furnace_id: int = Field(..., description="焦炉编号")
    mode: str = Field(..., pattern="^(manual|shadow|auto)$")
    operator: str = Field(..., description="操作人工号/姓名（审计用）")
    reason: str = Field("", description="切换原因")
