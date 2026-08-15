"""安全视觉AI路由（方案4.4.1节）。

- GET  /vision/alarms              视觉告警列表（安全帽/烟火/闯入/煤气泄漏等）
- POST /vision/alarms/{alarm_id}/ack  告警确认（处理人+处置意见）

告警由 models/vision/alarm_engine 产生并落库，本服务只提供查询与确认闭环。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.core.security import get_current_user
from services.api.schemas.vision import AckRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vision", tags=["安全视觉"])

# 告警场景（4.4.1节）
ALARM_SCENES = ("helmet", "fire_smoke", "intrusion", "gas_leak", "meter_reading", "coke_maturity")


@router.get("/alarms", summary="视觉告警列表")
def list_alarms(
    scene: str | None = Query(None, description=f"场景过滤: {'/'.join(ALARM_SCENES)}"),
    acked: bool | None = Query(None, description="是否已确认"),
    limit: int = 50,
    user: str = Depends(get_current_user),
):
    """查询视觉告警，支持按场景/确认状态过滤，按时间倒序。"""
    if scene and scene not in ALARM_SCENES:
        raise HTTPException(status_code=422, detail=f"未知场景: {scene}")
    # TODO: 从PostgreSQL vision_alarm表查询（含截图URL、摄像头位号、置信度）
    logger.info("查询视觉告警: scene=%s acked=%s user=%s", scene, acked, user)
    return {"alarms": [], "detail": "告警表待建（依赖数据底座）"}


@router.post("/alarms/{alarm_id}/ack", summary="视觉告警确认")
def ack_alarm(alarm_id: int, req: AckRequest, user: str = Depends(get_current_user)):
    """确认告警：记录处理人与处置意见；误报标记回流训练集迭代（每周重训消费）。"""
    # TODO: UPDATE vision_alarm SET acked=TRUE, handler=?, comment=?, is_false_positive=? WHERE id=?
    logger.info(
        "视觉告警确认: alarm=%s handler=%s false_positive=%s api_user=%s",
        alarm_id, req.handler, req.is_false_positive, user,
    )
    return {"alarm_id": alarm_id, "status": "acked"}
