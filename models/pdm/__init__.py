"""设备预测性维护 PdM（方案 4.3）：两级预警体系（V1.1 修订，RUL 后置）。

- level1 实时异常检测：孤立森林（anomaly_detect）
- level2 趋势预测 + ISO 10816 分级：LSTM（trend_forecast）
- level3 RUL：后置 2~3 年，故障样本 ≥50 例再立项（rul_estimator 仅占位）
"""

from .anomaly_detect import AnomalyDetector
from .trend_forecast import TrendForecaster, iso10816_grade

__all__ = ["AnomalyDetector", "TrendForecaster", "iso10816_grade"]
