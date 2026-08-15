"""设备预测性维护（PdM）路由（方案4.3节）。

- GET /pdm/devices                    监控设备列表（4.3.1节优先级清单）
- GET /pdm/devices/{device_id}/health 健康评分（异常检测+趋势预测综合）
- GET /pdm/alarms                     告警列表（两级预警体系，4.3.2节）

注：RUL剩余寿命估算为后置项（故障样本≥50例再立项），不在本版提供接口。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pdm", tags=["设备PdM"])

# 监控对象清单（4.3.1节），上线后迁移到PostgreSQL device表
DEVICE_REGISTRY = [
    {"device_id": "pusher_travel", "name": "推焦车走行机构", "priority": "P0",
     "sensors": ["vibration", "current", "temperature"]},
    {"device_id": "guide_grid", "name": "拦焦车导焦栅", "priority": "P0",
     "sensors": ["vibration", "displacement"]},
    {"device_id": "cdq_fan", "name": "干熄焦循环风机", "priority": "P0",
     "sensors": ["vibration_spectrum", "bearing_temp"]},
    {"device_id": "coal_screw", "name": "装煤车螺旋给料", "priority": "P1",
     "sensors": ["current", "rpm"]},
    {"device_id": "gas_blower", "name": "焦炉煤气鼓风机", "priority": "P1",
     "sensors": ["vibration", "bearing_temp", "flow"]},
    {"device_id": "chem_pump", "name": "化产离心泵", "priority": "P1",
     "sensors": ["vibration", "seal_temp"]},
    {"device_id": "belt_conveyor", "name": "皮带输送机", "priority": "P2",
     "sensors": ["vibration", "belt_deviation"]},
]


@router.get("/devices", summary="监控设备列表")
def list_devices(priority: str | None = Query(None, pattern="^P[012]$"),
                 user: str = Depends(get_current_user)):
    """返回监控设备清单，支持按优先级P0/P1/P2过滤。"""
    devices = DEVICE_REGISTRY
    if priority:
        devices = [d for d in devices if d["priority"] == priority]
    return {"devices": devices, "total": len(devices)}


@router.get("/devices/{device_id}/health", summary="设备健康评分")
def get_health(device_id: str, user: str = Depends(get_current_user)):
    """综合健康评分（0~100）：孤立森林异常分 + LSTM趋势外推 + ISO 10816振动分级。

    模型在 models/pdm/（anomaly_detect/trend_forecast），此处做调用编排。
    """
    if device_id not in {d["device_id"] for d in DEVICE_REGISTRY}:
        raise HTTPException(status_code=404, detail=f"设备不存在: {device_id}")
    # TODO: 取近7天传感器特征 → models.pdm.anomaly_detect + trend_forecast → 综合评分
    raise HTTPException(status_code=503, detail="健康评分模型未部署")


@router.get("/alarms", summary="PdM告警列表")
def list_alarms(
    level: str | None = Query(None, pattern="^(WARNING|DANGER)$"),
    device_id: str | None = None,
    limit: int = 50,
    user: str = Depends(get_current_user),
):
    """查询两级预警告警（4.3.2节：level1实时异常 / level2趋势+ISO10816分级）。"""
    # TODO: 从PostgreSQL pdm_alarm表查询，支持level/device_id过滤、按时间倒序
    logger.info("查询PdM告警: level=%s device=%s user=%s", level, device_id, user)
    return {"alarms": [], "detail": "告警表待建（依赖数据底座）"}
