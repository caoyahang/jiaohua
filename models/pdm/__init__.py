"""设备预测性维护 PdM（方案 4.3）：两级预警体系（V1.1 修订，RUL 后置）。

- level1 实时异常检测：孤立森林（anomaly_detect）
- level2 趋势预测 + ISO 10816 分级：LSTM（trend_forecast）
- level3 RUL：后置 2~3 年，故障样本 ≥50 例再立项（rul_estimator 仅占位）

Torch 相关对象按 PEP 562 懒加载（trend_forecast 依赖 torch），保证未安装
torch 时仍可独立导入 anomaly_detect 等轻量模块并跑单测（总纲§1）。
"""

from __future__ import annotations

from .anomaly_detect import AnomalyDetector

__all__ = ["AnomalyDetector", "TrendForecaster", "iso10816_grade"]


def __getattr__(name: str):
    """按需加载 Torch 相关趋势预测模块（方案§6.1）。"""
    if name in ("TrendForecaster", "iso10816_grade"):
        from . import trend_forecast

        return getattr(trend_forecast, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
