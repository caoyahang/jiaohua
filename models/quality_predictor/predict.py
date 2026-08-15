"""焦炭质量预测统一入口（方案 4.1.2 模型A，作为配煤优化器的"模拟器"）。

路由策略（按配置切换）：
  - empirical：强制走经验配煤模型（冷启动期，方案 4.1.6 投产前 0~6 月）
  - ml：强制走 LightGBM（达产期）
  - auto：按训练样本量自动切换 —— 有效样本 < min_samples_for_ml 时用经验模型，
    达到阈值后切换 LightGBM（试生产期平滑过渡）
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .empirical_model import TARGETS, EmpiricalQualityPredictor, SingleCoal

logger = logging.getLogger(__name__)

# auto 模式下切换到 ML 模型的最小有效样本量（方案 4.1.6：试生产期 200 组起训）
DEFAULT_MIN_SAMPLES_FOR_ML = 200


class QualityPredictor:
    """质量预测门面类：对内路由经验模型/LightGBM，对外暴露统一 predict 接口。"""

    def __init__(
        self,
        mode: str = "auto",
        model_dir: str = "artifacts/quality_predictor",
        empirical_coefficients: Optional[Dict[str, Dict[str, float]]] = None,
        min_samples_for_ml: int = DEFAULT_MIN_SAMPLES_FOR_ML,
    ):
        """
        :param mode: empirical / ml / auto
        :param model_dir: LightGBM 模型目录（train.py 输出）
        :param empirical_coefficients: 经验模型标定系数（见 empirical_model）
        :param min_samples_for_ml: auto 模式下启用 ML 模型的样本量阈值
        """
        if mode not in ("empirical", "ml", "auto"):
            raise ValueError(f"非法模式: {mode}")
        self.mode = mode
        self.min_samples_for_ml = min_samples_for_ml
        self.empirical = EmpiricalQualityPredictor(empirical_coefficients)
        self._ml_models: Dict[str, Any] = {}
        self._feature_columns: List[str] = []
        if mode in ("ml", "auto"):
            self._load_ml_models(model_dir)

    # ------------------------------------------------------------------ #
    def _load_ml_models(self, model_dir: str) -> None:
        """加载四个指标的 LightGBM 模型；文件缺失时降级为经验模型并告警。"""
        path = Path(model_dir)
        for target in TARGETS:
            pkl = path / f"lgbm_{target}.pkl"
            if pkl.exists():
                with open(pkl, "rb") as f:
                    bundle = pickle.load(f)
                self._ml_models[target] = bundle["model"]
                self._feature_columns = bundle["feature_columns"]
            else:
                logger.warning("未找到 %s 模型文件 %s，该指标将回退经验模型", target, pkl)

    @property
    def active_backend(self) -> str:
        """当前生效的后端（供日志/接口展示）。"""
        if self.mode == "empirical":
            return "empirical"
        if self.mode == "ml":
            return "lightgbm" if len(self._ml_models) == len(TARGETS) else "empirical(fallback)"
        # auto：四指标模型齐备才判定可用 ML；样本量判断交由调用方传入
        return "lightgbm" if len(self._ml_models) == len(TARGETS) else "empirical"

    def resolve_mode(self, n_training_samples: Optional[int] = None) -> str:
        """auto 模式下结合样本量决定路由。

        :param n_training_samples: 当前累计有效训练样本数；None 时仅看模型是否齐备
        """
        if self.mode != "auto":
            return "lightgbm" if self.active_backend.startswith("lightgbm") else "empirical"
        if n_training_samples is not None and n_training_samples < self.min_samples_for_ml:
            return "empirical"
        return self.active_backend if self.active_backend != "empirical(fallback)" else "empirical"

    # ------------------------------------------------------------------ #
    # 预测接口
    # ------------------------------------------------------------------ #
    def predict(
        self,
        coals: Optional[List[SingleCoal]] = None,
        ratios: Optional[List[float]] = None,
        features: Optional[pd.DataFrame] = None,
        n_training_samples: Optional[int] = None,
    ) -> Dict[str, float]:
        """统一预测入口。

        经验模型路径：传 coals + ratios（单种煤指标 + 配比）。
        ML 模型路径：传 features（特征 DataFrame，列序与训练一致，见 4.1.4 特征清单）。

        :return: {"M25": ..., "M10": ..., "CSR": ..., "CRI": ...}
        """
        backend = self.resolve_mode(n_training_samples)
        if backend == "lightgbm":
            if features is None:
                raise ValueError("ML 模式必须提供特征 DataFrame")
            return self._predict_ml(features)
        if coals is None or ratios is None:
            raise ValueError("经验模型模式必须提供 coals + ratios")
        return self.empirical.predict(coals, ratios)

    def _predict_ml(self, features: pd.DataFrame) -> Dict[str, float]:
        """LightGBM 四指标推理。"""
        X = features[self._feature_columns]
        return {
            target: round(float(self._ml_models[target].predict(X)[0]), 2)
            for target in TARGETS
        }
