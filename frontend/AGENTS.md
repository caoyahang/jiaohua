# 前端书写规范（frontend/）

> 适用范围：`frontend/` 四个模块（dashboard / blend_ui / furnace_ui / pdm_ui）。
> 上位规范：根目录 `AGENTS.md`（文档驱动总原则 §0、变更联动对照表 §0.3）对本目录**强制生效**，本文件只补充前端专属规则。
> 现状：四模块均为 React + TS 工程（2026-08-15 由 Vue 3 整体切换，方案修订记录第 10 条）；页面-接口对应关系维护在各目录 README。

## 1. 总原则：自用场景从简

- **信息密度优先于视觉效果**——给厂内人员天天用的工具，不是给客户演示的 Demo。
- 不做 3D 数字孪生（方案已后置）；驾驶舱用 ECharts 平面大屏。
- 技术栈固定为下表（方案§6.1），**除此之外不得新增依赖**；确需新增先改本表与方案§6.1 登记。

### 批准依赖清单

| 场景 | 技术 | 备注 |
|---|---|---|
| 响应式框架 | React 18 + TypeScript（strict） | 函数组件 + hooks |
| 脚手架 | Vite | |
| UI 框架 | Ant Design 5 | 表格一律用 AntD Table |
| 样式 | Tailwind CSS + Sass（仅全局样式/tokens） | 组件样式优先 Tailwind 类 |
| 样式覆盖 | styled-components | 覆盖 AntD/第三方样式时单独成文件（`*.styled.ts`） |
| 图表 | echarts + echarts-for-react | |
| 大屏组件库 | @jiaminghi/data-view-react 1.2.5 | **仅 dashboard 驾驶舱**（BorderBox/Decoration/DigitalFlop/ScrollBoard）；peerDeps 为 React16，安装走 legacy-peer-deps（dashboard/.npmrc 已配） |
| hooks 工具 | ahooks | 轮询用 useInterval/useRequest |
| 数据状态 | zustand | 必挂中间件：persist（登录态）+ devtools + subscribeWithSelector |
| 滚动条 | overlayscrollbars | 滚动区域统一封装 |
| 日历 | react-big-calendar | **批准但按需安装**：当前无日历页面，有页面需要时才进 package.json |
| 接口类型 | openapi-typescript（devDep） | 从后端 `/openapi.json` 生成 TS 类型，见 §2.1 |
| UI 自动化 | Playwright（devDep） | 见 §6 |
| 部署 | Nginx | build 产物为静态文件，由部署任务接 docker-compose |

### 环境与流程约定（不进代码库）

- AI 辅助编程：Copilot / Augment / Cursor / Gemini；串行思考 MCP（`@modelcontextprotocol/server-sequential-thinking`）
- 调试工具：zustand devtools（状态查看）、stagewise（LLM 微调页面）、LocatorJS（定位源代码）
- 团队协作：GitHub 仓库管理 + AI 协助修 Bug；版本发布走 Jenkins

## 2. 模块与接口对应

| 模块 | 页面 | 对应 API（`docs/API文档.md`，字段细节以 `services/api/routes/` 代码为准） |
|---|---|---|
| `dashboard/` | 全厂 KPI 一屏（K均/K安/K1/K2/K3、成本、能耗、告警汇总） | `GET /furnace/k-coefficients`、`GET /pdm/alarms`、`GET /vision/alarms` |
| `blend_ui/` | 配煤方案：输入目标质量 → 三套方案对比 → 确认执行 → 化验回流 | `POST /blend/optimize`、`GET /blend/recipes`、`POST /blend/feedback` |
| `furnace_ui/` | 炉温监控、AI 推荐值 vs 人工值、控制模式切换（manual/shadow/auto） | `GET /furnace/temp`、`GET /furnace/ai-setpoint`、`POST /furnace/control-mode` |
| `pdm_ui/` | 设备健康评分、两级告警列表与确认 | `GET /pdm/devices`、`GET /pdm/devices/{id}/health`、`GET /pdm/alarms` |

- 页面与 API 一一对应，对应关系维护在各目录 README；API 变更时按总纲 §0.3 同步。

### 2.1 接口契约 → TS 类型（Swagger 转 TS）

- 后端 FastAPI 自带 OpenAPI；`scripts/export_openapi.py` 导出到 `frontend/shared/openapi.json`，各工程 `npm run gen:api`（openapi-typescript）生成 `src/api/schema.d.ts`。
- **禁止手写与后端重复的接口请求/响应类型**；mock 数据必须符合 schema 类型（tsc 强制）。
- 已知现实：部分后端路由未声明 response_model，生成的类型偏宽松；后端补齐 response_model 后重新导出生成（属后端任务，不在前端越权改）。

## 3. 编码红线

1. **单文件 ≤ 400 行**（.tsx/.ts 均算）；超出必须拆分（拆子组件 / 抽 hooks / 抽常量）。
2. **功能逻辑不与样式写在一起**：样式集中在 Tailwind 类、`src/styles/*.scss`（全局/tokens）、`*.styled.ts`（styled-components）；组件文件只组装。
3. **禁止内联样式**（`style={{}}`）；动态尺寸等极少数例外须注释说明理由。
4. **所有颜色必须是 token**：`src/styles/tokens.ts` 单一存放，Tailwind config 与 AntD ConfigProvider theme 同源引用；组件内禁止出现十六进制/rgb 颜色字面量。
   - **跨模块同源规则**：base `colors` 组四模块同名色值必须一致（改 base = 四个模块一起改）；模块专属扩展放进独立导出组（如 dashboard 的 `darkColors`、pdm_ui 的 `orange`），不回写 base。门禁 `scripts/check_frontend_tokens.py` 自动比对，同名不同值即 fail。
5. **接口类型来自契约**（见 §2.1）。
6. 半成品必须显式 TODO，禁止用假数据冒充完成；mock 数据必须挂「演示数据」角标（MockBadge）。

## 4. 给工艺人员用的设计纪律

- 配煤师/调火工是核心用户：**5 分钟能上手的复杂度**；专业术语用厂内习惯叫法（火道温度、直行温度、K3），不用 AI 黑话。
- **所有 AI 输出旁边必须有"依据/解释"入口**：配煤方案带 SHAP 中文说明，炉温推荐值带与人工值对比——信任 > 精度（方案§15）。
- 涉及控制的页面（furnace_ui）：控制模式状态必须常显；shadow/auto 模式下 AI 推荐值与当前实际设定值同屏对比；切手动按钮视觉上永远可达（DCS 硬切换说明，本界面不做软按钮替代）。

## 5. 告警与刷新

- 告警类页面刷新延迟 ≤10 秒（方案§7.2 阶段六验收），用轮询即可（ahooks useInterval），不上 WebSocket（自用从简）。
- 告警展示带级别（WARNING/DANGER）、时间、确认状态；误报可标记回流（视觉告警 ack 接口）。

## 6. UI 自动化测试（Playwright）

- **新生成页面必配 Playwright 冒烟用例**：页面渲染 + 关键交互各 1 条，放 `tests/smoke.spec.ts`。
- 验收命令：`npm run build && npx tsc --noEmit && npx playwright test` 全绿。

## 7. 变更联动（前端特有）

- 页面用到的接口变更 → 以 `services/api/routes/` 代码为准改调用，同步更新本目录 README 的接口清单，并重新执行 §2.1 的类型生成。
- KPI 展示口径（K 系数、成本降低）必须与 `docs/操作手册.md` 验收章节一致，前端不得自创计算口径。
- 本规则文件变更 → 在 `docs/README.md` 变更记录留痕（总纲 §2）。
