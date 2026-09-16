#!/usr/bin/env bash
# =============================================================================
# model_retrain.sh - 模型重训脚本（配煤质量预测模型，周度触发）
#
# 用法: ./scripts/model_retrain.sh [模型名]     默认 quality_predictor
# 调用方: services/scheduler 每周任务 / 增量学习缓冲区满时手动触发
# 流程: 训练 -> 评估(KPI验收 10.1节) -> MLflow注册staging -> 达标才promote
# =============================================================================
set -euo pipefail

MODEL_NAME="${1:-quality_predictor}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-http://localhost:5000}"
export PYTHONPATH="${PROJECT_ROOT}"

echo "===== 模型重训: ${MODEL_NAME} ($(date '+%F %T')) ====="

case "${MODEL_NAME}" in
    quality_predictor)
        # 配煤质量预测：LightGBM全量重训（4.1.6节）
        # 训练数据 = 本厂实际配煤+化验数据（含工艺侧特征：结焦时间/火温/堆密度/熄焦方式）
        echo "----- 启动训练 -----"
        # train.py 只接受 --config（见 models/quality_predictor/train.py main）；
        # 训练过程内部已输出各指标 R²/MAE（含离线评估口径）
        python -m models.quality_predictor.train --config config/model_config.yaml

        echo "----- 离线评估（KPI验收口径，见方案10.1节） -----"
        # TODO: models/quality_predictor/evaluate.py 尚无 CLI 入口（无 main/argparse），
        #   待补充后启用独立评估；当前评估指标由 train.py 训练时输出。
        # TODO: 评估达标（如CSR/CRI预测R²≥合同阈值）后执行MLflow promote:
        #   mlflow models transition ... --stage Production
        ;;
    pdm_anomaly)
        # PdM异常检测（孤立森林）重训：无监督，仅需正常工况数据
        echo "----- PdM异常检测模型重训 -----"
        # TODO: models/pdm/anomaly_detect.py 尚无 CLI 入口（无 main），待接通后启用：
        #   python -m models.pdm.anomaly_detect --retrain
        ;;
    *)
        echo "[错误] 未知模型: ${MODEL_NAME}（支持: quality_predictor / pdm_anomaly）" >&2
        exit 1
        ;;
esac

echo "===== 重训流程结束: ${MODEL_NAME} ====="
