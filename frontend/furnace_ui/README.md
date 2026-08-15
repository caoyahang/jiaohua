# furnace_ui —— 焦炉监控界面

焦炉 AI 加热控制的调火工操作界面（V1.1 阶段四）。

## 技术栈

- React 18 + TypeScript + Ant Design + Tailwind + ECharts（温度趋势曲线、设定值对比图）；栈细则见 `frontend/AGENTS.md`
- 自用场景从简，由后端工程师兼任开发（V1.1 §8.1）；**不含数字孪生**

## 页面与接口（已实现，2026-08-15）

| 页面 | 内容 | 关联接口 | 后端状态 → 前端行为 |
|---|---|---|---|
| 炉温实时监控 | 机/焦侧火道温度曲线、煤气流量、吸力、残氧；换向期灰色标记；10s 轮询 | `GET /furnace/temp` | 恒 503 → 必走 mock（演示数据角标） |
| AI 推荐值 | AI setpoint vs 实际值同屏对比、钳位标记、模型版本 | `GET /furnace/ai-setpoint` | 可用（占位值）→ 真实优先，断网兜底 mock |
| 控制模式 | manual / shadow / auto 状态展示与软切换（双人确认） | `POST /furnace/control-mode`（请求体 `{furnace_id, mode, operator, reason}`，以代码为准） | 可用 → 真实调用 |
| K 系数看板 | K均 / K安 / K1 / K2 / K3 班次趋势与目标线（K均≥0.90、K3≥0.95） | `GET /furnace/k-coefficients` | 恒 503 → 必走 mock（演示数据角标） |

安全红线（V1.1 §4.2.6）：安全联锁永远走 DCS 硬回路；「一键切手动」为 DCS 侧硬切换，
不在本界面实现软按钮替代；本界面所有 AI 操作仅影响设定值，且 DCS 侧硬钳位。
实现自检：全工程无「切手动」按钮；控制模式徽标在 App 顶部**全站常显**；
切换需操作人+复核人双人确认且不得同一人。

## 本地运行

```bash
npm install
npm run dev    # 代理 /auth /blend /furnace /pdm /vision → http://localhost:8000
npm run build
```

mock 降级约定与 blend_ui 一致，见 `src/api/client.js`。
