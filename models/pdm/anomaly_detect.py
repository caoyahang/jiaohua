"""level1 实时异常检测：孤立森林（方案 4.3.2 PdMModel.level1_realtime_alarm）。

目标：毫秒级发现突发异常（如振动突然飙升、轴承温度突变）。
监控对象：P0 推焦车走行机构 / 拦焦车导焦栅 / 干熄焦循环风机，
          P1 装煤车螺旋给料 / 煤气鼓风机 / 化产离心泵（方案 4.3.1）。
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# 异常判定阈值（孤立森林 decision_function 得分，越低越异常）
# TODO(标定): 按各设备基线数据的得分分布确定分位点阈值（如正常段 1% 分位）
DEFAULT_ANOMALY_THRESHOLD = -0.5

# 每台设备的监测特征（对齐 4.3.1 监测参数）
DEFAULT_FEATURES = ["vibration", "bearing_temp", "current"]


class AnomalyDetector:
    """单设备孤立森林异常检测器（每台 P0/P1 设备各持有一个实例）。"""

    def __init__(
        self,
        device_id: str,
        features: Optional[List[str]] = None,
        contamination: float = 0.02,
        n_estimators: int = 200,
        anomaly_threshold: float = DEFAULT_ANOMALY_THRESHOLD,
    ):
        """
        :param device_id: 设备编号
        :param features: 监测特征列（振动/轴承温度/电流等）
        :param contamination: 训练数据中预估异常占比
        :param anomaly_threshold: 异常得分阈值
        """
        self.device_id = device_id
        self.features = features or list(DEFAULT_FEATURES)
        self.threshold = anomaly_threshold
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42,
        )
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit_baseline(self, normal_data: pd.DataFrame) -> None:
        """用健康运行段数据训练基线。

        :param normal_data: 设备健康期监测数据（已剔除停机/检修段）
        TODO(数据): 健康段筛选规则待与点检系统对接（剔除检修工单时间窗）。
        """
        X = normal_data[self.features].to_numpy()
        self.model.fit(X)
        self._fitted = True
        logger.info("[%s] 孤立森林基线训练完成: %d 样本 × %d 特征",
                    self.device_id, len(X), len(self.features))

    # ------------------------------------------------------------------ #
    def level1_realtime_alarm(self, sensor_data: Dict[str, float]) -> Optional[Dict[str, str]]:
        """实时异常判定（方案 4.3.2 level1）。

        :param sensor_data: 单条实时监测值 {特征名: 数值}
        :return: 异常时返回告警字典，正常返回 None
        """
        if not self._fitted:
            raise RuntimeError(f"[{self.device_id}] 模型未训练，先调用 fit_baseline")
        x = np.array([[sensor_data[f] for f in self.features]])
        score = float(self.model.decision_function(x)[0])
        if score < self.threshold:
            return {
                "level": "WARNING",
                "device_id": self.device_id,
                "score": f"{score:.3f}",
                "msg": "振动异常，建议检查",
            }
        return None

    # ------------------------------------------------------------------ #
    def save(self, path: str) -> None:
        """序列化保存。"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "features": self.features,
                         "threshold": self.threshold, "device_id": self.device_id}, f)

    @classmethod
    def load(cls, path: str) -> "AnomalyDetector":
        """加载已训练检测器。"""
        with open(path, "rb") as f:
            bundle = pickle.load(f)
        obj = cls(device_id=bundle["device_id"], features=bundle["features"],
                  anomaly_threshold=bundle["threshold"])
        obj.model = bundle["model"]
        obj._fitted = True
        return obj
