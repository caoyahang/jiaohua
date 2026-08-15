"""焦炭质量预测模型（方案4.1，应用一·模型A）。

冷启动期使用经验配煤模型（empirical_model），数据积累后切换 LightGBM（train/predict）。
对外统一入口为 predict.QualityPredictor，predict 接口在两套模型间保持一致。
"""

from .predict import QualityPredictor
from .empirical_model import EmpiricalQualityPredictor

__all__ = ["QualityPredictor", "EmpiricalQualityPredictor"]
