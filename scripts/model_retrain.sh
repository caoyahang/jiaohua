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
        python -m models.quality_predictor.train \
            --output-dir "${MODEL_DIR:-./data/models}/${MODEL_NAME}" \
            --mlflow-uri "${MLFLOW_TRACKING_URI}"

        echo "----- 离线评估（KPI验收口径，见方案10.1节） -----"
        python -m models.quality_predictor.evaluate \
            --model-dir "${MODEL_DIR:-./data/models}/${MODEL_NAME}"
        # TODO: 评估达标（如CSR/CRI预测R²≥合同阈值）后执行MLflow promote:
        #   mlflow models transition ... --stage Production
        ;;
    pdm_anomaly)
        # PdM异常检测（孤立森林）重训：无监督，仅需正常工况数据
        echo "----- PdM异常检测模型重训 -----"
        python -m models.pdm.anomaly_detect --retrain
        ;;
    *)
        echo "[错误] 未知模型: ${MODEL_NAME}（支持: quality_predictor / pdm_anomaly）" >&2
        exit 1
        ;;
esac

echo "===== 重训流程结束: ${MODEL_NAME} ====="
