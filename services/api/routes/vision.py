"""安全视觉AI路由（方案4.4.1节）。

- GET  /vision/alarms              视觉告警列表（安全帽/烟火/闯入/煤气泄漏等）
- POST /vision/alarms/{alarm_id}/ack  告警确认（处理人+处置意见）

告警由 models/vision/alarm_engine 产生并落库，本服务只提供查询与确认闭环。
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.core.security import get_current_user
from services.api.db.connections import get_pg_conn
from services.api.schemas.vision import AckRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vision", tags=["安全视觉"])

# 告警场景（4.4.1节，与 docs/API文档.md §5 取值口径一致）
ALARM_SCENES = ("helmet", "fire", "intrusion", "gas_leak", "gauge", "coke_cake")


@router.get("/alarms", summary="视觉告警列表")
def list_alarms(
    scene: str | None = Query(None, description=f"场景过滤: {'/'.join(ALARM_SCENES)}"),
    area: str | None = Query(None, description="区域过滤（如 焦炉炉顶）"),
    date_from: date | None = None,
    date_to: date | None = None,
    acknowledged: bool | None = Query(None, description="是否已确认"),
    limit: int = 50,
    user: str = Depends(get_current_user),
):
    """查询视觉告警（vision_alarm 表，方案§3.4.7），按时间倒序。"""
    if scene and scene not in ALARM_SCENES:
        raise HTTPException(status_code=422, detail=f"未知场景: {scene}")
    import psycopg2.extras  # noqa: PLC0415

    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = (
                "SELECT id, camera_id, scene, area, label, confidence, level,"
                " message, snapshot_url, acknowledged, is_false_positive,"
                " created_at FROM vision_alarm"
            )
            clauses: list[str] = []
            params: list = []
            if scene:
                clauses.append("scene = %s")
                params.append(scene)
            if area:
                clauses.append("area = %s")
                params.append(area)
            if date_from:
                clauses.append("created_at >= %s")
                params.append(date_from)
            if date_to:
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
    logger.info("查询视觉告警: scene=%s acknowledged=%s 命中=%d user=%s", scene, acknowledged, len(rows), user)
    return {
        "items": [
            {
                "alarm_id": r["id"],
                "scene": r["scene"],
                "area": r["area"],
                "camera_id": r["camera_id"],
                "label": r["label"],
                "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
                "level": r["level"],
                "msg": r["message"],
                "snapshot_url": r["snapshot_url"],
                "acknowledged": r["acknowledged"],
                "is_false_positive": r["is_false_positive"],
                "ts": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    }


@router.post("/alarms/{alarm_id}/ack", summary="视觉告警确认")
def ack_alarm(alarm_id: int, req: AckRequest, user: str = Depends(get_current_user)):
    """确认告警：记录处理人与处置意见；误报标记回流训练集迭代（每周重训消费）。"""
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vision_alarm SET acknowledged=TRUE, handler=%s,"
                " ack_comment=%s, is_false_positive=%s, acked_at=NOW()"
                " WHERE id=%s AND acknowledged=FALSE",
                (req.handler, req.comment, req.is_false_positive, alarm_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                raise HTTPException(
                    status_code=404, detail=f"告警不存在或已确认: {alarm_id}"
                )
        conn.commit()
    finally:
        conn.close()
    logger.info(
        "视觉告警确认: alarm=%s handler=%s false_positive=%s api_user=%s",
        alarm_id, req.handler, req.is_false_positive, user,
    )
    return {"alarm_id": alarm_id, "status": "acked"}
