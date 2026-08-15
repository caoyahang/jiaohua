# pdm_ui —— 设备健康界面

设备预测性维护（PdM）监控界面（V1.1 阶段五）。

## 技术栈

- React 18 + TypeScript + Ant Design + Tailwind + ECharts（健康评分仪表、振动趋势、ISO 10816 分区着色）；栈细则见 `frontend/AGENTS.md`
- 自用场景从简，由后端工程师兼任开发（V1.1 §8.1）；**不含数字孪生**

## 页面与接口（已实现，2026-08-15）

| 页面 | 内容 | 关联接口 | 后端状态 → 前端行为 |
|---|---|---|---|
| 设备总览 | P0/P1/P2 设备健康评分列表与状态（running/stopped/maintenance/fault） | `GET /pdm/devices` | 设备注册信息真实可用；运行字段（健康评分/振动/温度）后端未出 → mock 补齐，恒挂演示数据角标 |
| 单机详情 | 健康评分仪表、振动速度趋势（ISO 10816 四区着色：良好/注意/不合格/危险）、轴承温度、电机电流 | `GET /pdm/devices/{id}/health` | 恒 503 → 必走 mock |
| 告警中心 | 两级预警列表（实时异常 / 趋势分级），确认与处置记录；10s 轮询 | `GET /pdm/alarms` | 真实可用但返回空占位；确认为前端本地状态（**后端 PdM ack 接口待建**，见 AlarmCenterView TODO） |
| 检修计划 | 基于告警生成检修建议，关联上次/下次检修日期 | 由告警数据派生 | 全部 mock，恒挂演示数据角标 |

注意（V1.1 §4.3）：不展示 RUL 剩余寿命预测——故障样本不足，该能力后置 2~3 年（样本 ≥50 例再立项）；
误报率是第一优先级指标（< 15%，误报失控 = 告警无人看）。实现自检：UI 无任何 RUL 展示。

告警推送企业微信/钉钉由后端完成，本界面仅做展示与确认。

## 本地运行

```bash
npm install
npm run dev    # 代理 /auth /blend /furnace /pdm /vision → http://localhost:8000
npm run build
```

mock 降级约定与 blend_ui 一致，见 `src/api/client.js`。
