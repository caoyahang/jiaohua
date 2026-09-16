# dashboard —— 全厂运营总览

面向厂内管理与运行人员的日常运营页面（方案§7.2 阶段六）。目录名保留 `dashboard` 以避免部署路径变化，页面形态为常规企业管理后台，不使用全屏驾驶舱设计。

## 技术栈

- React 18 + TypeScript + Ant Design + Tailwind + ECharts；栈细则见 `frontend/AGENTS.md`
- 数据源：FastAPI 后端 `services/api/`
- 自用场景从简：不含 DataV 装饰组件和 3D 数字孪生，桌面与移动端均采用自然滚动的响应式布局

## 页面与接口（2026-08-30 运营页改版）

单页运营总览实现见 `src/pages/DashboardPage.tsx`。顶部是普通应用导航和手动刷新入口，正文依次展示 KPI 卡片、热工/推焦趋势、焦炭质量趋势、安全摘要和最新视觉告警表格。全页每 10 秒轮询，各数据区块独立降级，单个接口失败不阻断其他区块。

| 区块 | 内容 | 数据来源 | 后端状态 → 前端行为 |
|---|---|---|---|
| 运营 KPI | 配煤成本节约、质量预测准确率、煤气消耗、非计划停机、安全告警数 | 聚合接口（后端尚无） | 固定 mock 并显示角标；告警数由视觉 + PdM 告警实时汇总 |
| 热工趋势 | K均 / K安 近 7 天趋势，K均目标 0.90 | `GET /furnace/k-coefficients` | 503/断网 → mock |
| 推焦趋势 | K1 / K2 / K3 近 7 天趋势，K3 目标 0.95 | `GET /furnace/k-coefficients` | 503/断网 → mock |
| 质量趋势 | M25/M10/CSR/CRI 实测与预测（近 10 批次） | 后端暂无 `coke_quality` 查询接口 | 固定 mock，TODO：新增查询接口后接入 |
| 安全与设备告警 | 视觉场景分布、PdM 未确认摘要 | `GET /vision/alarms`、`GET /pdm/alarms` | 真实查表；503/断网 → mock |
| 最新视觉告警 | 最新 10 条告警，含时间、场景、区域、级别和确认状态 | `GET /vision/alarms` | 同上；使用 AntD Table 静态展示，不自动轮播 |

刷新延迟要求 `< 10 秒`，当前轮询间隔为 10 秒；页面保留“演示数据”角标，避免把 mock 误认为现场数据。

## 本地运行

```bash
npm install
npm run dev
npm run typecheck
npm run build
npm run test:e2e
```

Vite 开发代理把 `/auth`、`/blend`、`/furnace`、`/pdm`、`/vision` 转发到 `http://localhost:8000`。mock 降级约定见 `src/api/client.ts`。
