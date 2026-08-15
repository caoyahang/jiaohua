"""LightGBM 焦炭质量四指标（M25/M10/CSR/CRI）训练脚本（方案 4.1.6 试生产阶段）。

流程：读数据 → 特征工程 → 逐指标训练 → 评估 → MLflow 记录 → 保存模型。

数据来源：本厂实际配煤+化验数据（含工艺侧特征：结焦时间/火温/堆密度/熄焦方式），
200~500 组起步。注意：小焦炉数据须先标定与大炉的 CSR/CRI 系统偏差后再混入训练。

用法（骨架）：
    python -m models.quality_predictor.train --config configs/quality_train.yaml
"""

from __future__ import annotations

import argparse
import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from .empirical_model import TARGETS

logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    """训练配置（由 YAML 加载）。"""

    data_path: str = "data/blend_quality.csv"   # 配煤+化验数据（或SQL导出）
    feature_columns: List[str] = field(default_factory=list)  # 为空则自动取数值列
    target_columns: List[str] = field(default_factory=lambda: list(TARGETS))
    test_size: float = 0.2
    random_state: int = 42
    model_dir: str = "artifacts/quality_predictor"
    mlflow_experiment: str = "coke-quality-predictor"
    mlflow_model_name: str = "quality-predictor-lgbm"
    lgbm_params: Dict[str, Any] = field(default_factory=lambda: {
        "objective": "regression",
        "n_estimators": 500,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
    })


def load_config(path: str) -> TrainConfig:
    """从 YAML 加载训练配置。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = TrainConfig()
    for key, value in raw.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    return cfg


def load_dataset(cfg: TrainConfig) -> pd.DataFrame:
    """读取配煤+化验数据集。

    TODO(数据底座): 改为从 PostgreSQL 配煤方案表(3.4.1) JOIN 焦炭质量化验表(3.4.2)，
    并关联炉温记录表(3.4.3)补齐工艺侧特征（结焦时间/火温/堆密度/熄焦方式）。
    """
    df = pd.read_csv(cfg.data_path)
    logger.info("数据集加载完成: %d 行 × %d 列", len(df), df.shape[1])
    return df


def build_features(df: pd.DataFrame, cfg: TrainConfig) -> tuple[pd.DataFrame, List[str]]:
    """特征工程（方案 4.1.4 约 40 维特征）。

    覆盖：单种煤基础指标加权、镜质组反射率分布直方图(8~12维)、配比特征(配比熵/
    最大占比/方差)、成本特征、煤岩组合特征、工艺特征、炼焦工艺特征、约束特征。

    TODO(特征): 配比熵、Rmax 分布直方图展开、流动性指数(G×Y/Ad)等派生特征
    目前假定上游 ETL 已落库为列；此处仅做列选择与缺失值处理，后续补派生逻辑。
    """
    feature_cols = cfg.feature_columns or [
        c for c in df.columns if c not in cfg.target_columns and df[c].dtype != object
    ]
    X = df[feature_cols].copy()
    X = X.fillna(X.median(numeric_only=True))
    logger.info("特征维度: %d", len(feature_cols))
    return X, feature_cols


def train_single_target(
    X_train: pd.DataFrame, y_train: pd.Series, cfg: TrainConfig
) -> lgb.LGBMRegressor:
    """训练单指标 LightGBM 回归模型。"""
    model = lgb.LGBMRegressor(**cfg.lgbm_params)
    model.fit(X_train, y_train)
    return model


def evaluate_model(model: lgb.LGBMRegressor, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    """计算 R² 与 MAE。"""
    pred = model.predict(X_test)
    return {
        "r2": float(r2_score(y_test, pred)),
        "mae": float(mean_absolute_error(y_test, pred)),
    }


def train(config_path: str) -> Dict[str, lgb.LGBMRegressor]:
    """主训练流程：逐指标训练 → MLflow 记录 → 保存。"""
    cfg = load_config(config_path)
    df = load_dataset(cfg)
    X, feature_cols = build_features(df, cfg)

    model_dir = Path(cfg.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    models: Dict[str, lgb.LGBMRegressor] = {}

    mlflow.set_experiment(cfg.mlflow_experiment)
    for target in cfg.target_columns:
        y = df[target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=cfg.test_size, random_state=cfg.random_state
        )
        with mlflow.start_run(run_name=f"quality-{target}"):
            model = train_single_target(X_train, y_train, cfg)
            metrics = evaluate_model(model, X_test, y_test)

            mlflow.log_params({"target": target, "n_features": len(feature_cols), **cfg.lgbm_params})
            mlflow.log_metrics(metrics)
            mlflow.lightgbm.log_model(model, artifact_path=f"model-{target}",
                                      registered_model_name=f"{cfg.mlflow_model_name}-{target}")
            logger.info("[%s] R²=%.4f MAE=%.4f", target, metrics["r2"], metrics["mae"])

            # 本地 pickle 备份（含特征列，保证推理时列序一致）
            with open(model_dir / f"lgbm_{target}.pkl", "wb") as f:
                pickle.dump({"model": model, "feature_columns": feature_cols}, f)
        models[target] = model

    logger.info("全部指标训练完成，模型已保存至 %s", model_dir)
    return models


def main() -> None:
    parser = argparse.ArgumentParser(description="焦炭质量预测模型训练")
    parser.add_argument("--config", required=True, help="训练配置 YAML 路径")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    train(args.config)


if __name__ == "__main__":
    main()
