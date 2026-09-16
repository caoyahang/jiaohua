"""设备预测性维护（PdM）契约（方案§4.3）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PdmDevice(BaseModel):
    """监控设备（GET /pdm/devices 响应元素，方案§4.3.1 监控对象清单）。"""

    device_id: str
    name: str
    priority: str = Field(..., description="优先级：P0/P1/P2")
    sensors: list[str] = Field(..., description="监测传感器类型")


class DevicesResponse(BaseModel):
    """GET /pdm/devices 响应。"""

    devices: list[PdmDevice]
    total: int


class PdmAlarm(BaseModel):
    """PdM 告警（GET /pdm/alarms 响应元素，方案§4.3.2 两级预警）。"""

    alarm_id: int
    equipment_id: int
    level: str = Field(..., description="告警级别：WARNING/DANGER")
    source: str = Field(..., description="来源：level1_anomaly/level2_trend_forecast")
    metric: str | None = None
    metric_value: float | None = None
    threshold: float | None = None
    iso10816_zone: str | None = None
    msg: str | None = None
    acknowledged: bool
    handler: str | None = None
    ack_comment: str | None = None
    acked_at: str | None = None
    ts: str


class PdmAlarmsResponse(BaseModel):
    """GET /pdm/alarms 响应。"""

    items: list[PdmAlarm]
