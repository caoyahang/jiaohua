"""帧推理 + 结果回调（方案 4.4.1）：边缘节点逐帧推理，命中目标回调告警引擎。

部署形态：边缘推理盒子（ONNX Runtime / ultralytics），按摄像头通道起流；
推理结果不直接告警，统一交给 alarm_engine 做时间窗去重与推送。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """单帧检测结果。"""

    camera_id: str
    scenario: str                # helmet / fire / intrusion
    label: str                   # 命中类别
    confidence: float
    bbox: List[float]            # [x1, y1, x2, y2]
    timestamp: float = field(default_factory=time.time)


class VisionInference:
    """单路摄像头推理器。"""

    def __init__(
        self,
        weights_path: str,
        camera_id: str,
        scenario: str,
        conf_threshold: float = 0.5,
        on_detection: Optional[Callable[[List[Detection]], None]] = None,
    ):
        """
        :param weights_path: 训练导出的权重（.pt / .onnx）
        :param camera_id: 摄像头编号（告警定位用）
        :param scenario: 场景标识（透传给告警引擎选规则）
        :param conf_threshold: 置信度阈值
        :param on_detection: 检测结果回调（接 alarm_engine.ingest）
        """
        self.model = YOLO(weights_path)
        self.camera_id = camera_id
        self.scenario = scenario
        self.conf_threshold = conf_threshold
        self.on_detection = on_detection

    # ------------------------------------------------------------------ #
    def infer_frame(self, frame: np.ndarray) -> List[Detection]:
        """单帧推理。

        :param frame: BGR 图像（OpenCV 格式）
        :return: 命中目标列表（已按置信度过滤）
        """
        t0 = time.perf_counter()
        results = self.model.predict(frame, conf=self.conf_threshold, verbose=False)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        detections: List[Detection] = []
        for box in results[0].boxes:
            detections.append(Detection(
                camera_id=self.camera_id,
                scenario=self.scenario,
                label=self.model.names[int(box.cls)],
                confidence=float(box.conf),
                bbox=[round(float(v), 1) for v in box.xyxy[0].tolist()],
            ))
        if elapsed_ms > 1000:
            logger.warning("[%s] 单帧推理耗时 %.0fms，可能影响响应时限", self.camera_id, elapsed_ms)
        return detections

    # ------------------------------------------------------------------ #
    def run_stream(self, frame_source) -> None:
        """视频流主循环（骨架）。

        :param frame_source: 可迭代帧源（如 RTSP 拉流封装，yield np.ndarray）
        TODO(部署): 接 RTSP 拉流 + 断流重连 + 抽帧（响应要求内按 2~5fps 抽帧即可，
        不必逐帧）；多路摄像头由进程池各自起 VisionInference。
        """
        for frame in frame_source:
            detections = self.infer_frame(frame)
            if detections and self.on_detection:
                self.on_detection(detections)
