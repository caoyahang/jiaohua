# blend_ui —— 智能配煤界面

配煤师日常操作界面，**整个项目的第一个里程碑**（V1.1 阶段二/三）。第一版要求足够简单：配煤师 5 分钟上手。

## 技术栈

- React 18 + TypeScript + Ant Design + Tailwind + ECharts（配比饼图、SHAP 条形图、成本对比图）；栈细则见 `frontend/AGENTS.md`
- 自用场景从简，由后端工程师兼任开发（V1.1 §8.1）；**不含数字孪生**

## 规划页面

| 页面 | 内容 | 关联接口 |
|---|---|---|
| 质量预测 | 输入配煤比 → 显示预测 M25/M10/CSR/CRI + SHAP 解释 | `POST /blend/optimize`（quality 预测链路） |
| 方案优化 | 输入目标质量/煤价/库存 → AI 返回 3 套方案（成本最优/质量最稳/综合推荐）→ 人工确认 | `POST /blend/optimize` |
| 历史方案 | 配煤方案查询、执行记录、AI方案 vs 配煤师方案成本对比 | `GET /blend/recipes` |
| 结果回写 | 化验结果录入/确认（对接 LIMS 电子接口），触发增量学习 | `POST /blend/feedback` |

关键交互原则：AI 建议 + 人工确认，配煤师始终有最终决定权（信任过渡期，V1.1 §13.2）。

## 接口清单（以 services/api 实际代码为准）

| 页面 | 接口 | 后端状态 | 前端行为 |
|---|---|---|---|
| 登录 | `POST /auth/login` → `{access_token, token_type, expires_in}` | 可用 | 不做 mock 降级；后端不可达时进入"演示模式"（stores/auth.js） |
| 质量预测 | 后端暂无独立预测接口 | 未接通 | `api/index.js#predictQuality` 纯演示实现，固定挂 `__mock`（TODO：方案§4.1.6 DOE 标定后接通） |
| 方案优化 | `POST /blend/optimize` → `{solutions, model_version, compute_time_ms}` | 恒 503（优化器未编排） | 必走 mock（api/mock.js#mockOptimize） |
| 历史方案 | `GET /blend/recipes?furnace_id=&limit=` → `{recipes}` | 依赖 PG，不可用则 503 | 503/断网自动降级 mock |
| 结果回写 | `POST /blend/feedback` → `{batch_no, status:"accepted", detail}` | 可用 | mock 仅断网兜底 |

mock 降级统一约定见 `src/api/client.js`：2xx 返回真实数据；网络异常或 503 返回 mock 并挂 `__mock: true`；
401 清 token 跳登录页；其余错误抛带 detail 的 Error。带 `__mock` 的响应必须显示 MockBadge「演示数据」。

## 本地运行

```bash
npm install
npm run dev    # 代理 /auth /blend /furnace /pdm /vision → http://localhost:8000
npm run build
```
