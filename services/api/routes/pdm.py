"""设备预测性维护（PdM）路由（方案4.3节）。

- GET /pdm/devices                    监控设备列表（4.3.1节优先级清单）
- GET /pdm/devices/{device_id}/health 健康评分（异常检测+趋势预测综合）
- GET /pdm/alarms                     告警列表（两级预警体系，4.3.2节）

注：RUL剩余寿命估算为后置项（故障样本≥50例再立项），不在本版提供接口。
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.core.security import get_current_user
from services.api.db.connections import get_pg_conn
from services.api.schemas.pdm import DevicesResponse, PdmAlarmsResponse

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


@router.get("/devices", response_model=DevicesResponse, summary="监控设备列表")
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


@router.get("/alarms", response_model=PdmAlarmsResponse, summary="PdM告警列表")
def list_alarms(
    equipment_id: int | None = None,
    level: str | None = Query(None, pattern="^(WARNING|DANGER)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    acknowledged: bool | None = None,
    limit: int = 50,
    user: str = Depends(get_current_user),
):
    """查询两级预警告警（4.3.2节），响应契约见 docs/API文档.md §5。

    数据源：PostgreSQL pdm_alarm 表（方案§3.4.6）；level 为严重度，
    两级分类在 source 字段（level1_anomaly 实时异常 / level2_trend_forecast 趋势分级）。
    """
    import psycopg2.extras  # noqa: PLC0415

    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = (
                "SELECT id, equipment_id, level, source, metric, metric_value,"
                " threshold, iso10816_zone, message, acknowledged, handler,"
                " ack_comment, acked_at, created_at FROM pdm_alarm"
            )
            clauses: list[str] = []
            params: list = []
            if equipment_id is not None:
                clauses.append("equipment_id = %s")
                params.append(equipment_id)
            if level:
                clauses.append("level = %s")
                params.append(level)
            if date_from:
                clauses.append("created_at >= %s")
                params.append(date_from)
            if date_to:
                # date_to 当日闭区间：< 次日零点的写法避免漏掉当天尾盘告警
                clauses.append("created_at < %s::date + 1")
                params.append(date_to)
            if acknowledged is not None:
                clauses.append("acknowledged = %s")
                params.append(acknowledged)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()
    logger.info("查询PdM告警: equipment=%s level=%s 命中=%d user=%s",
                equipment_id, level, len(rows), user)
    return {"items": [_to_alarm_item(r) for r in rows]}


def _to_alarm_item(r: dict) -> dict:
    """pdm_alarm 行 → API文档§5 响应项（额外字段为前端详情页透传）。"""
    return {
        "alarm_id": r["id"],
        "equipment_id": r["equipment_id"],
        "level": r["level"],
        "source": r["source"],
        "metric": r["metric"],
        "metric_value": r["metric_value"],
        "threshold": r["threshold"],
        "iso10816_zone": r["iso10816_zone"],
        "msg": r["message"],
        "acknowledged": r["acknowledged"],
        "handler": r["handler"],
        "ack_comment": r["ack_comment"],
        "acked_at": r["acked_at"].isoformat() if r["acked_at"] else None,
        "ts": r["created_at"].isoformat(),
    }
