"""焦炭质量预测模型评估：R²/MAE/交叉验证 + SHAP 可解释性分析（方案 4.1.2 模型C基础）。"""

from __future__ import annotations

import argparse
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score

logger = logging.getLogger(__name__)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """计算 R² / MAE / RMSE 三项回归指标。"""
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def cross_validate_model(
    model: Any, X: pd.DataFrame, y: pd.Series, n_splits: int = 5, random_state: int = 42
) -> Dict[str, float]:
    """K 折交叉验证（R²）。

    注意样本量 200~500 组时折数不宜过大，保持每折 ≥ 40 样本。
    """
    n_splits = min(n_splits, max(2, len(X) // 40))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = cross_val_score(model, X, y, cv=kf, scoring="r2")
    return {
        "cv_r2_mean": float(scores.mean()),
        "cv_r2_std": float(scores.std()),
        "cv_folds": float(n_splits),
    }


def evaluate_all_targets(
    models: Dict[str, Any], X: pd.DataFrame, df: pd.DataFrame
) -> Dict[str, Dict[str, float]]:
    """对四指标（M25/M10/CSR/CRI）逐一输出测试集指标 + 交叉验证结果。"""
    report: Dict[str, Dict[str, float]] = {}
    for target, model in models.items():
        y = df[target]
        pred = model.predict(X)
        metrics = regression_metrics(y.to_numpy(), np.asarray(pred))
        metrics.update(cross_validate_model(model, X, y))
        report[target] = metrics
        logger.info(
            "[%s] R²=%.3f MAE=%.3f CV-R²=%.3f±%.3f",
            target, metrics["r2"], metrics["mae"],
            metrics["cv_r2_mean"], metrics["cv_r2_std"],
        )
    return report


def shap_summary(
    model: Any,
    X: pd.DataFrame,
    target: str,
    output_dir: str = "artifacts/quality_predictor/shap",
    max_samples: int = 500,
) -> pd.DataFrame:
    """生成 SHAP 摘要图并返回特征重要性表。

    用途：向配煤师解释"为什么模型预测 CSR 是 66.8"，并支撑配煤优化器
    explainer 的边际贡献分析（方案 4.1.2 模型C）。

    TODO(可视化): 接前端后改为输出 SHAP force_plot 交互页面数据。
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    sample = X.sample(n=min(max_samples, len(X)), random_state=42) if len(X) > max_samples else X
    import shap  # noqa: PLC0415  # 懒加载：总纲§1
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)

    importance = pd.DataFrame({
        "feature": X.columns,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    # 保存 beeswarm 摘要图
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure()
    shap.summary_plot(shap_values, sample, show=False)
    fig_path = out / f"shap_summary_{target}.png"
    plt.savefig(fig_path, bbox_inches="tight", dpi=150)
    plt.close()
    logger.info("[%s] SHAP 摘要图已保存: %s", target, fig_path)
    return importance


def load_models(model_dir: str) -> tuple[Dict[str, Any], List[str]]:
    """加载四指标 LightGBM 模型（与 predict.py / incremental.py 加载逻辑对齐）。

    Args:
        model_dir: 模型目录（train.py 输出目录）。

    Returns:
        (models, feature_columns)：{指标: 模型} 与特征列名列表。
    """
    model_dir = Path(model_dir)
    models: Dict[str, Any] = {}
    feature_columns: List[str] = []
    for target in ("M25", "M10", "CSR", "CRI"):
        pkl = model_dir / f"lgbm_{target}.pkl"
        if not pkl.exists():
            logger.warning("模型文件缺失: %s，该指标跳过评估", pkl)
            continue
        with open(pkl, "rb") as f:
            bundle = pickle.load(f)
        models[target] = bundle["model"]
        feature_columns = bundle["feature_columns"]
    return models, feature_columns


def main() -> None:
    """CLI 入口：离线评估已训练模型（方案§10.1 KPI 验收口径）。

    用法：
        python -m models.quality_predictor.evaluate \\
            --model-dir artifacts/quality_predictor --data data/eval.csv
    """
    parser = argparse.ArgumentParser(description="焦炭质量预测模型离线评估（方案§10.1 KPI验收）")
    parser.add_argument("--model-dir", default="artifacts/quality_predictor", help="模型目录")
    parser.add_argument("--data", required=True, help="评估数据 CSV（含特征列与 M25/M10/CSR/CRI 标签）")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    models, feature_columns = load_models(args.model_dir)
    if not models:
        raise SystemExit("未找到任何已训练模型，请先运行 train.py 训练")
    if not feature_columns:
        raise SystemExit("模型缺失特征列，无法评估")

    df = pd.read_csv(args.data)
    X = df[feature_columns]
    report = evaluate_all_targets(models, X, df)
    for target, metrics in report.items():
        logger.info(
            "[%s] R²=%.3f MAE=%.3f CV-R²=%.3f±%.3f",
            target, metrics["r2"], metrics["mae"],
            metrics["cv_r2_mean"], metrics["cv_r2_std"],
        )


if __name__ == "__main__":
    main()
