# dashboard —— 领导驾驶舱

全厂 KPI 一屏展示（V1.1 §7.2 阶段六）。

## 技术栈

- React 18 + TypeScript + Ant Design + Tailwind + ECharts 平面大屏（信息密度高、维护成本低）；栈细则见 `frontend/AGENTS.md`
- DataV 大屏组件库 `@jiaminghi/data-view-react@1.2.5`（面板边框 BorderBox12 / 标题装饰 Decoration8 / KPI 翻牌 DigitalFlop / 告警轮播 ScrollBoard）；包无 TS 类型，本地声明在 `src/types/data-view-react.d.ts`；peerDeps 为 React16，安装走 `legacy-peer-deps`（本目录 `.npmrc` 已配）
- 数据源：FastAPI 后端（`services/api/`）+ Grafana 嵌入面板
- 自用场景从简：不设专职前端，由后端工程师兼任（V1.1 §8.1）；**不含 3D 数字孪生**（V1.1 已后置/可选，确有需要再外包）

## 页面与接口（已实现，2026-08-15；大屏视觉重设计 2026-08-16）

单页深色大屏（`src/pages/DashboardPage.tsx`），不做多路由；全页 10 秒轮询。
布局（2026-08-16 重设计）：**1920×1080 一屏无滚动**（flex 视口适配，更小屏允许纵向滚动）——
顶部标题栏（Decoration 装饰线 + 发光标题 + 实时时钟）→ 三栏网格（左：KPI 翻牌卡 + 质量看板；
中：焦炉加热系统示意 FurnaceSchematic（BorderBox8 流光边框）+ 热工 KPI；右：安全看板 + 视觉告警
ScrollBoard 轮播表）→ 底部通栏推焦 KPI。面板统一 DataV BorderBox 发光边框（Panel.tsx），
图表 fillHeight 自适应（ChartCard 内置 ResizeObserver 驱动 resize）。
布局：顶部标题栏（居中平台名 + 实时时钟/数据同步时间，`ScreenHeader.tsx`）→ 三栏网格（左：KPI 卡片 + 质量看板；中：工艺示意图 + 热工 KPI；右：安全看板 + 视觉告警滚动列表）→ 底部通栏推焦 KPI；小屏单列纵向滚动。
面板样式统一为 `Panel.tsx`（DataV BorderBox12 科技边框 + 标题左侧色条），KPI 数值用 DigitalFlop 翻牌器、告警列表用 ScrollBoard 轮播表，整屏点阵纹理底见 `screen.styled.ts`；颜色全部取 `src/styles/tokens.ts` 的 darkColors token。

| 区块 | 内容 | 数据来源 | 后端状态 → 前端行为 |
|---|---|---|---|
| 全厂总览 | 配煤成本节约、质量预测准确率、煤气消耗、非计划停机、安全告警数 | 聚合接口（**后端尚无**） | 固定 mock，角标常显；告警数走 `GET /vision/alarms` + `GET /pdm/alarms`（真实查询，503/断网 → mock） |
| 工艺示意图 | 焦炉加热系统 2D SVG（炭化室/机·焦侧燃烧室火道/煤气管道/烟道/集气管），叠加实时火道温度、煤气流量、烟道吸力、集气管压力、残氧 | `GET /furnace/temp`（组件 `FurnaceSchematic.tsx`） | 恒 503 → 必走 mock |
| 热工 KPI | K均 / K安 趋势（目标 K均 ≥ 0.90 红色目标线） | `GET /furnace/k-coefficients` | 恒 503 → 必走 mock |
| 推焦 KPI | K1 / K2 / K3 趋势（目标 K3 ≥ 0.95 红色目标线） | `GET /furnace/k-coefficients` | 恒 503 → 必走 mock |
| 质量看板 | 焦炭 M25/M10/CSR/CRI 实际 vs 预测（近 10 批次） | **原规划 `GET /blend/recipes` 不含质量字段，已改为固定 mock**（字段对齐 `coke_quality` 表） | 固定 mock，TODO：待后端新增 coke_quality 查询接口 |
| 安全看板 | 视觉告警场景分布 + PdM 未确认摘要 | `GET /vision/alarms`、`GET /pdm/alarms` | 真实查询 vision_alarm / pdm_alarm 表（契约见 `docs/API文档.md` §5）；503/断网 → mock。视觉告警确认接口 `POST /vision/alarms/{id}/ack` 已可用，本页无确认交互故未接 |
| 视觉告警滚动列表 | 最新 10 条视觉 AI 告警自动滚动（悬停暂停，组件 `AlarmScrollList.tsx`） | `GET /vision/alarms` | 同上，503/断网 → mock |

要求：数据刷新延迟 < 10 秒（已实现 10s 轮询）；关键告警区基本响应式（网格自动换行）。

## 本地运行

```bash
npm install
npm run dev    # 端口 5174，代理 /auth /blend /furnace /pdm /vision → http://localhost:8000
npm run build
```

mock 降级约定与 blend_ui 一致，见 `src/api/client.ts`。
