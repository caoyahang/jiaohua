"""增量学习机制（方案 4.1.7，关键闭环）。

每次出焦化验结果回来 → 对比预测值 → 误差超过阈值 → 入误差缓冲 →
缓冲区满 50 条 → LightGBM 热启动增量训练（init_model=旧模型，小学习率防遗忘）。

由调度层（APScheduler / API 回调）在化验数据入库后调用 on_new_coke_data。
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 默认误差阈值（超阈值才入缓冲区）；正式运行按指标分别配置
DEFAULT_ERROR_THRESHOLDS: Dict[str, float] = {
    "M25": 2.0,   # 抗碎强度绝对误差 > 2 个百分点
    "M10": 1.0,
    "CSR": 3.0,
    "CRI": 2.0,
}
BUFFER_FLUSH_SIZE = 50            # 缓冲区满 50 条触发增量训练（方案 4.1.7）
INCREMENTAL_LEARNING_RATE = 0.01  # 小学习率防灾难性遗忘
INCREMENTAL_N_ESTIMATORS = 50     # 每次增量新增的树数量


class IncrementalLearner:
    """质量预测模型增量学习器。"""

    def __init__(
        self,
        model_dir: str = "artifacts/quality_predictor",
        error_thresholds: Optional[Dict[str, float]] = None,
        buffer_flush_size: int = BUFFER_FLUSH_SIZE,
        on_retrain: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        :param model_dir: 模型目录（与 train.py 输出一致）
        :param error_thresholds: 各指标误差阈值
        :param buffer_flush_size: 触发增量训练的缓冲区大小
        :param on_retrain: 增量训练完成后的回调（如通知 MLflow 登记新版本）
        """
        self.model_dir = Path(model_dir)
        self.error_thresholds = error_thresholds or dict(DEFAULT_ERROR_THRESHOLDS)
        self.buffer_flush_size = buffer_flush_size
        self.on_retrain = on_retrain
        self.models: Dict[str, Any] = {}
        self.feature_columns: List[str] = []
        self.error_buffer: List[Dict[str, Any]] = []
        self._load_models()

    # ------------------------------------------------------------------ #
    def _load_models(self) -> None:
        """加载当前在线模型（与 predict.py 的加载逻辑对齐）。"""
        for target, thr in self.error_thresholds.items():
            pkl = self.model_dir / f"lgbm_{target}.pkl"
            if not pkl.exists():
                logger.warning("模型文件缺失: %s，该指标不参与增量学习", pkl)
                continue
            with open(pkl, "rb") as f:
                bundle = pickle.load(f)
            self.models[target] = bundle["model"]
            self.feature_columns = bundle["feature_columns"]

    # ------------------------------------------------------------------ #
    def on_new_coke_data(self, blend_features: pd.Series, actual_quality: Dict[str, float]) -> Dict[str, float]:
        """新化验结果回流（方案 4.1.7 第 1~4 步）。

        :param blend_features: 该炉配煤+工艺特征（与训练特征同构）
        :param actual_quality: 实测 {"M25": ..., "M10": ..., "CSR": ..., "CRI": ...}
        :return: 各指标绝对误差
        """
        X = pd.DataFrame([blend_features[self.feature_columns].to_dict()])
        errors: Dict[str, float] = {}
        for target, model in self.models.items():
            if target not in actual_quality:
                continue
            pred = float(model.predict(X)[0])
            error = abs(pred - actual_quality[target])
            errors[target] = round(error, 3)
            if error > self.error_thresholds[target]:
                self.error_buffer.append({
                    "target": target,
                    "features": blend_features.to_dict(),
                    "actual": actual_quality[target],
                    "pred": pred,
                    "error": error,
                })
                logger.info("[%s] 误差 %.3f 超阈值，入缓冲区（当前 %d 条）",
                            target, error, len(self.error_buffer))

        if len(self.error_buffer) >= self.buffer_flush_size:
            self._incremental_train()
            self.error_buffer = []
        return errors

    # ------------------------------------------------------------------ #
    def _incremental_train(self) -> None:
        """增量训练（方案 4.1.7 第 4 步）。

        按目标分组缓冲数据，用 init_model 热启动 + 小学习率微调，
        在旧模型基础上新增少量树，避免灾难性遗忘。

        TODO(验证): 增量训练后应在保留验证集上回归测试，性能不回退才替换在线模型
        （当前直接落盘，后续加模型版本闸门）。
        """
        buf = pd.DataFrame(self.error_buffer)
        stats: Dict[str, Any] = {}
        for target, group in buf.groupby("target"):
            if target not in self.models:
                continue
            old_model = self.models[target]
            X_new = pd.DataFrame(list(group["features"]))[self.feature_columns]
            y_new = group["actual"].astype(float)

            params = dict(old_model.get_params())
            params["learning_rate"] = INCREMENTAL_LEARNING_RATE
            params["n_estimators"] = INCREMENTAL_N_ESTIMATORS
            new_model = lgb.LGBMRegressor(**params)
            new_model.fit(X_new, y_new, init_model=old_model.booster_)
            self.models[target] = new_model
            stats[target] = {"n_samples": len(group), "mean_error": float(group["error"].mean())}
            logger.info("[%s] 增量训练完成：%d 条样本，平均误差 %.3f",
                        target, len(group), stats[target]["mean_error"])

        self._save_models()
        if self.on_retrain:
            self.on_retrain(stats)

    def _save_models(self) -> None:
        """增量后的模型落盘（覆盖在线版本）。"""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        for target, model in self.models.items():
            with open(self.model_dir / f"lgbm_{target}.pkl", "wb") as f:
                pickle.dump({"model": model, "feature_columns": self.feature_columns}, f)
