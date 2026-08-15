"""AI焦化厂智能化平台 —— 算法模型层（models）。

按《AI焦化厂智能化落地方案 V1.1》第四章组织：

- quality_predictor   应用一·模型A：焦炭质量预测（经验模型冷启动 + LightGBM）
- blending_optimizer  应用一·模型B/C：配煤成本优化（GA）与SHAP解释
- furnace_control     应用二：焦炉AI智能加热控制（LSTM + MPC + 影子模式）
- pdm                 应用三：设备预测性维护（两级预警，RUL后置）
- vision              应用四：安全视觉AI（YOLOv8）
- chemical_recovery   应用六：化产回收AI优化（二期）
"""
