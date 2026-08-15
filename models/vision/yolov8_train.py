"""YOLOv8 训练骨架（方案 4.4.1）：安全帽/烟火/闯入三类数据集。

数据集按 ultralytics YOLO 格式组织（images/ + labels/ + data.yaml），
三类场景各自训练独立权重，部署到边缘推理节点。

用法（骨架）：
    python -m models.vision.yolov8_train --scenario helmet --data datasets/helmet/data.yaml
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from ultralytics import YOLO

logger = logging.getLogger(__name__)

# 三类场景的类别定义（与 data.yaml 的 names 保持一致）
SCENARIOS: Dict[str, List[str]] = {
    "helmet": ["person", "helmet", "no_helmet", "reflective_vest"],  # 安全帽/反光衣
    "fire": ["flame", "smoke"],                                      # 烟火识别
    "intrusion": ["person", "crossing_line"],                        # 违规闯入/跨越
}

# 各场景响应要求（秒，方案 4.4.1）——训练导出时用于校验端侧推理耗时
RESPONSE_BUDGET_SECONDS = {"helmet": 3, "fire": 5, "intrusion": 3}


@dataclass
class VisionTrainConfig:
    """训练配置。"""

    scenario: str = "helmet"
    data_yaml: str = ""                # 数据集 data.yaml 路径
    base_weights: str = "yolov8n.pt"   # 边缘部署优先轻量模型；精度不足再升 yolov8s
    epochs: int = 100
    imgsz: int = 640
    batch: int = 16
    device: str = "0"                  # GPU id；"cpu" 仅调试用
    project: str = "artifacts/vision"
    export_onnx: bool = True           # 导出 ONNX 供 ONNX Runtime 推理（方案 6.1）


def train(cfg: VisionTrainConfig) -> Path:
    """训练单场景模型并导出 ONNX。

    TODO(数据): 三类数据集需现场采集标注（每类 ≥2000 张起步，覆盖夜班红外/
    雨雾/粉尘工况）；标注规范与数据增强策略待视觉供应商联合制定。
    TODO(校验): 导出后在边缘盒子实测帧率，须满足 RESPONSE_BUDGET_SECONDS。
    """
    if cfg.scenario not in SCENARIOS:
        raise ValueError(f"未知场景 {cfg.scenario}，可选: {list(SCENARIOS)}")
    if not cfg.data_yaml:
        raise ValueError("必须指定 --data 数据集 yaml 路径")

    model = YOLO(cfg.base_weights)
    results = model.train(
        data=cfg.data_yaml,
        epochs=cfg.epochs,
        imgsz=cfg.imgsz,
        batch=cfg.batch,
        device=cfg.device,
        project=cfg.project,
        name=f"{cfg.scenario}_v1",
    )
    best = Path(results.save_dir) / "weights" / "best.pt"
    logger.info("[%s] 训练完成，最优权重: %s", cfg.scenario, best)

    if cfg.export_onnx:
        onnx_path = YOLO(str(best)).export(format="onnx", imgsz=cfg.imgsz)
        logger.info("[%s] ONNX 已导出: %s", cfg.scenario, onnx_path)
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="安全视觉 YOLOv8 训练")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS))
    parser.add_argument("--data", required=True, help="数据集 data.yaml 路径")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--base", default="yolov8n.pt", help="预训练权重")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    train(VisionTrainConfig(scenario=args.scenario, data_yaml=args.data,
                            epochs=args.epochs, base_weights=args.base))


if __name__ == "__main__":
    main()
