"""RTSP 视频流采集（供视觉AI推理消费）。

依据《AI焦化厂智能化落地方案 V1.1》：
- 3.2.1：视频监控系统走 RTSP / GB28181，实时流
- 4.4.1：YOLOv8 识别场景（安全帽/烟火/闯入/表计/焦饼成熟度），响应 <3~30s

设计要点：拉流线程只保留最新帧（frame_buffer_size=2），推理消费不掉
直接丢旧帧，防止队列积压导致告警延迟；帧通过回调交给 vision 推理模块。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# OpenCV 为运行时依赖（拉流解码）；骨架允许未安装时导入本模块做静态检查
try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


@dataclass
class CameraDef:
    """单路摄像头定义（对应 dcs_tags.yaml 的 rtsp_cameras 一条记录）。"""

    camera_id: str
    description: str
    scene: str          # furnace_top / belt_corridor / gas_holder ...
    url_env: str        # 存放 RTSP 地址的环境变量名（地址不落仓库）


@dataclass
class FramePacket:
    """一帧数据包，交给 vision 推理模块。"""

    camera_id: str
    scene: str
    frame: Any          # numpy.ndarray (H, W, C)，BGR
    capture_ts: float   # 采集时间戳（秒）
    frame_seq: int      # 自增帧序号


def load_cameras(tags_yaml: str | Path) -> List[CameraDef]:
    """从 config/dcs_tags.yaml 加载摄像头列表。"""
    with open(tags_yaml, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [
        CameraDef(
            camera_id=c["camera_id"],
            description=c.get("description", ""),
            scene=c.get("scene", ""),
            url_env=c["url_env"],
        )
        for c in cfg.get("rtsp_cameras", [])
    ]


class RtspCapture:
    """单路 RTSP 拉流器（每路摄像头一个实例，内部一个拉流线程）。

    用法::

        capture = RtspCapture(camera, on_frame=vision_infer.enqueue)
        capture.start()   # 后台线程拉流
        ...
        capture.stop()
    """

    def __init__(
        self,
        camera: CameraDef,
        on_frame: Optional[Callable[[FramePacket], None]] = None,
        reconnect_interval: float = 10.0,
        frame_buffer_size: int = 2,
    ) -> None:
        """
        Args:
            camera: 摄像头定义。
            on_frame: 帧回调（推给 vision 推理；应非阻塞，推理侧自己排队）。
            reconnect_interval: 断流重连间隔（秒）。
            frame_buffer_size: OpenCV 内部缓冲帧数，小值保证只取最新帧。
        """
        self.camera = camera
        self.on_frame = on_frame
        self.reconnect_interval = reconnect_interval
        self.frame_buffer_size = frame_buffer_size
        self._cap: Any = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._frame_seq = 0

    @property
    def rtsp_url(self) -> str:
        """RTSP 地址（从环境变量读取）。"""
        url = os.environ.get(self.camera.url_env, "")
        if not url:
            raise RuntimeError(
                f"环境变量 {self.camera.url_env} 未设置（摄像头 {self.camera.camera_id}）"
            )
        return url

    def start(self) -> None:
        """启动后台拉流线程。"""
        if cv2 is None:
            raise RuntimeError("opencv-python 未安装，无法拉流")
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name=f"rtsp-{self.camera.camera_id}", daemon=True
        )
        self._thread.start()
        logger.info("RTSP 拉流已启动: %s (%s)", self.camera.camera_id, self.camera.description)

    def stop(self) -> None:
        """停止拉流并释放资源。"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._release()

    def _loop(self) -> None:
        """拉流主循环：连接 → 循环读帧 → 回调；断流自动重连。"""
        while self._running:
            try:
                self._open()
                while self._running:
                    ok, frame = self._cap.read()
                    if not ok:
                        raise IOError("RTSP 读帧失败（断流）")
                    self._frame_seq += 1
                    if self.on_frame is not None:
                        self.on_frame(
                            FramePacket(
                                camera_id=self.camera.camera_id,
                                scene=self.camera.scene,
                                frame=frame,
                                capture_ts=time.time(),
                                frame_seq=self._frame_seq,
                            )
                        )
            except Exception:
                logger.exception(
                    "RTSP 断流: %s，%.1f 秒后重连",
                    self.camera.camera_id, self.reconnect_interval,
                )
                self._release()
                time.sleep(self.reconnect_interval)

    def _open(self) -> None:
        """打开 RTSP 流并收紧内部缓冲。

        TODO: 按场景做抽帧——安全帽/闯入场景 25fps 全量推理浪费 GPU，
        可按 2~5fps 抽帧；烟火识别需保证帧率以防漏检（响应 <5s）。
        """
        self._cap = cv2.VideoCapture(self.rtsp_url)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, self.frame_buffer_size)
        if not self._cap.isOpened():
            self._release()
            raise ConnectionError(f"RTSP 打开失败: {self.camera.camera_id}")

    def _release(self) -> None:
        """释放 VideoCapture（幂等）。"""
        if self._cap is not None:
            try:
                self._cap.release()
            finally:
                self._cap = None


class RtspCaptureManager:
    """多路摄像头统一管理：按 dcs_tags.yaml 批量起停拉流器。"""

    def __init__(
        self,
        tags_yaml: str | Path = "config/dcs_tags.yaml",
        on_frame: Optional[Callable[[FramePacket], None]] = None,
    ) -> None:
        self.captures: Dict[str, RtspCapture] = {
            cam.camera_id: RtspCapture(cam, on_frame=on_frame)
            for cam in load_cameras(tags_yaml)
        }

    def start_all(self) -> None:
        """启动全部摄像头拉流（单路失败不影响其他路，由各自线程内重连）。"""
        for cid, cap in self.captures.items():
            try:
                cap.start()
            except Exception:
                logger.exception("RTSP 启动失败: %s（已跳过）", cid)

    def stop_all(self) -> None:
        """停止全部拉流。"""
        for cap in self.captures.values():
            cap.stop()
