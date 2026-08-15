"""安全视觉契约（方案§4.4.1）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AckRequest(BaseModel):
    """告警确认请求。"""

    handler: str = Field(..., description="处理人")
    comment: str = Field("", description="处置意见")
    is_false_positive: bool = Field(False, description="是否误报（回流用于模型迭代）")
