"""安全视觉契约（方案§4.4.1）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AckRequest(BaseModel):
    """告警确认请求。"""

    handler: str = Field(..., description="处理人")
    comment: str = Field("", description="处置意见")
    is_false_positive: bool = Field(False, description="是否误报（回流用于模型迭代）")


class VisionAlarm(BaseModel):
    """视觉告警（GET /vision/alarms 响应元素，方案§3.4.7/§4.4.1）。"""

    alarm_id: int
    scene: str
    area: str | None = None
    camera_id: str
    label: str | None = None
    confidence: float | None = None
    level: str | None = None
    msg: str | None = None
    snapshot_url: str | None = None
    acknowledged: bool
    is_false_positive: bool
    ts: str


class VisionAlarmsResponse(BaseModel):
    """GET /vision/alarms 响应。"""

    items: list[VisionAlarm]


class AckResponse(BaseModel):
    """POST /vision/alarms/{id}/ack 响应。"""

    alarm_id: int
    status: str
