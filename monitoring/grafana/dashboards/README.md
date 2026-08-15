# Grafana Dashboards

本目录存放 Grafana 仪表盘的 JSON 导出文件（数据源：Prometheus，见 `../prometheus.yml`）。
Grafana 服务见 `docker-compose.yml`（端口 3000）。

## 规划仪表盘

| 仪表盘 | 内容 | 对应需求 |
|---|---|---|
| 数据底座监控 | 采集在线率、采集延迟、点位失败数、数据质量校验命中率 | V1.1 §3.3 数据治理标准（在线率 ≥ 99%、延迟 ≤ 5秒） |
| API 服务监控 | 请求量、平均响应时间（目标 < 500ms）、模型推理延迟（目标 < 1秒） | V1.1 §10.2 系统可用性指标 |
| 焦炉加热监控 | 火道温度趋势、AI setpoint vs 实际值、控制模式（manual/ai_shadow/ai_auto）、K均/K安 | V1.1 §4.2 |
| 设备 PdM 监控 | P0 设备健康评分、振动分级（ISO 10816）、告警统计与误报率 | V1.1 §4.3 |
| 模型监控 | 预测误差趋势、模型漂移检测指标、重训记录 | V1.1 §7.2 阶段七 |

## 使用说明

1. `docker compose up -d grafana prometheus` 启动后，访问 `http://localhost:3000`
2. 添加 Prometheus 数据源（地址 `http://prometheus:9090`）
3. 将本目录下的仪表盘 JSON 通过 Grafana UI「Import」导入

> 自用场景从简：领导驾驶舱优先用 Grafana 搭建，复杂交互再补轻量 React 页面（V1.1 §8.1）。
> 3D 数字孪生已后置/可选，不在本目录规划范围内。

TODO: 阶段一数据底座上线后导出首个「数据底座监控」仪表盘 JSON 至本目录。
