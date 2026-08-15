# dashboard —— 领导驾驶舱

全厂 KPI 一屏展示（V1.1 §7.2 阶段六）。

## 技术栈

- React 18 + TypeScript + Ant Design + Tailwind + ECharts 平面大屏（信息密度高、维护成本低）；栈细则见 `frontend/AGENTS.md`
- 数据源：FastAPI 后端（`services/api/`）+ Grafana 嵌入面板
- 自用场景从简：不设专职前端，由后端工程师兼任（V1.1 §8.1）；**不含 3D 数字孪生**（V1.1 已后置/可选，确有需要再外包）

## 页面与接口（已实现，2026-08-15）

单页深色大屏（`src/pages/DashboardPage.tsx`），不做多路由；全页 10 秒轮询。

| 区块 | 内容 | 数据来源 | 后端状态 → 前端行为 |
|---|---|---|---|
| 全厂总览 | 配煤成本节约、质量预测准确率、煤气消耗、非计划停机、安全告警数 | 聚合接口（**后端尚无**） | 固定 mock，角标常显；告警数走 `GET /vision/alarms`（占位 → mock） |
| 热工 KPI | K均 / K安 趋势（目标 K均 ≥ 0.90 红色目标线） | `GET /furnace/k-coefficients` | 恒 503 → 必走 mock |
| 推焦 KPI | K1 / K2 / K3 趋势（目标 K3 ≥ 0.95 红色目标线） | `GET /furnace/k-coefficients` | 恒 503 → 必走 mock |
| 质量看板 | 焦炭 M25/M10/CSR/CRI 实际 vs 预测（近 10 批次） | **原规划 `GET /blend/recipes` 不含质量字段，已改为固定 mock**（字段对齐 `coke_quality` 表） | 固定 mock，TODO：待后端新增 coke_quality 查询接口 |
| 安全看板 | 视觉 AI 告警滚动列表 + 场景分布 + PdM 未确认摘要 | `GET /vision/alarms`、`GET /pdm/alarms` | 真实请求，空占位/503 → mock |

要求：数据刷新延迟 < 10 秒（已实现 10s 轮询）；关键告警区基本响应式（网格自动换行）。

## 本地运行

```bash
npm install
npm run dev    # 端口 5174，代理 /auth /blend /furnace /pdm /vision → http://localhost:8000
npm run build
```

mock 降级约定与 blend_ui 一致，见 `src/api/client.js`。
