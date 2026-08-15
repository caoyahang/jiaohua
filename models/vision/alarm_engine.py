"""告警引擎（方案 4.4.1）：响应 <5 秒、时间窗去重、推送 Redis 队列 / 企业微信（预留）。

设计要点：
  - 推理结果先进引擎，按 (摄像头, 场景, 类别) 做时间窗去重 —— 同一路持续
    告警只在窗口期结束后重新推送，避免刷屏
  - 告警从产生到入 Redis 队列的链路预算 <5 秒（烟火场景红线）
  - 推送通道：Redis 队列（已落地）/ 企业微信 webhook（预留接口）
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import redis

from .inference import Detection

logger = logging.getLogger(__name__)

# 告警链路时间预算（秒）：从帧推理到入队不超过该值
RESPONSE_BUDGET_SECONDS = 5.0
# 去重时间窗（秒）：同一 (camera, scenario, label) 在窗口内只推一次
DEDUP_WINDOW_SECONDS = 300.0
# Redis 告警队列键
REDIS_ALARM_QUEUE = "vision:alarms"


@dataclass
class AlarmEvent:
    """一条待推送告警。"""

    camera_id: str
    scenario: str
    label: str
    confidence: float
    level: str                   # INFO / WARNING / DANGER
    message: str
    timestamp: float = field(default_factory=time.time)


# 各命中类别 → 告警级别与文案模板
ALARM_RULES: Dict[str, Dict[str, str]] = {
    "no_helmet": {"level": "WARNING", "message": "检测到未佩戴安全帽人员"},
    "flame": {"level": "DANGER", "message": "检测到明火，立即处置"},
    "smoke": {"level": "WARNING", "message": "检测到烟雾，请核查"},
    "crossing_line": {"level": "WARNING", "message": "检测到违规闯入/跨越"},
}


class AlarmEngine:
    """视觉告警引擎：去重 + 分级 + 推送。"""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        dedup_window: float = DEDUP_WINDOW_SECONDS,
        wecom_webhook: Optional[str] = None,
    ):
        """
        :param redis_client: Redis 连接（告警队列）；None 时仅记日志（调试模式）
        :param dedup_window: 去重时间窗（秒）
        :param wecom_webhook: 企业微信机器人 webhook（预留，暂未启用）
        """
        self.redis = redis_client
        self.dedup_window = dedup_window
        self.wecom_webhook = wecom_webhook
        self._last_push: Dict[Tuple[str, str, str], float] = {}

    # ------------------------------------------------------------------ #
    def ingest(self, detections: List[Detection]) -> List[AlarmEvent]:
        """接收一帧的检测结果，产出去重后的告警并推送。

        :return: 实际推送的告警列表
        """
        start = time.perf_counter()
        pushed: List[AlarmEvent] = []
        for det in detections:
            rule = ALARM_RULES.get(det.label)
            if rule is None:
                continue  # 非告警类别（如正常佩戴安全帽）直接忽略
            if self._is_duplicated(det):
                continue
            event = AlarmEvent(
                camera_id=det.camera_id, scenario=det.scenario, label=det.label,
                confidence=det.confidence, level=rule["level"],
                message=f"{rule['message']}（摄像头 {det.camera_id}）",
            )
            self._push(event)
            pushed.append(event)

        elapsed = time.perf_counter() - start
        if elapsed > RESPONSE_BUDGET_SECONDS:
            logger.error("告警链路耗时 %.2fs 超过 %ds 预算", elapsed, RESPONSE_BUDGET_SECONDS)
        return pushed

    # ------------------------------------------------------------------ #
    def _is_duplicated(self, det: Detection) -> bool:
        """时间窗去重：同 (摄像头, 场景, 类别) 窗口期内只告警一次。"""
        key = (det.camera_id, det.scenario, det.label)
        last = self._last_push.get(key, 0.0)
        if det.timestamp - last < self.dedup_window:
            return True
        self._last_push[key] = det.timestamp
        return False

    # ------------------------------------------------------------------ #
    def _push(self, event: AlarmEvent) -> None:
        """推送 Redis 队列；企业微信通道预留。

        TODO(推送): 企业微信 webhook 联调（self.wecom_webhook），DANGER 级
        告警需 @ 安全员；接入短信/电话兜底通道由运维侧决定。
        """
        payload = json.dumps(asdict(event), ensure_ascii=False)
        if self.redis is not None:
            self.redis.lpush(REDIS_ALARM_QUEUE, payload)
        logger.warning("[告警][%s] %s (置信度 %.2f)", event.level, event.message, event.confidence)
