# 后端书写规范（services/）

> 适用范围：`services/api/`、`services/scheduler/`。
> 上位规范：根目录 `AGENTS.md`（文档驱动总原则 §0、通用 Python 规范 §1、变更联动对照表 §0.3）对本目录**强制生效**，本文件只补充后端专属规则，不重复总纲内容。

## 1. 结构与职责

- `api/main.py`：只做装配（注册路由、CORS、中间件、全局异常处理、健康检查、启动日志）。
- `api/routes/`：每个 AI 应用一个文件（blend / furnace / pdm / vision），新增应用先在后端加路由文件，再登记 `docs/API文档.md`。
- `api/schemas/`：pydantic 请求/响应契约，按应用分文件（auth/blend/furnace/vision）。**路由文件禁止再 inline 定义 pydantic 模型**。
- `api/db/connections.py`：PG/TDengine/Redis 连接工厂（懒加载驱动、失败抛 503、连接串脱敏）。路由与 main.py 的连接创建一律走这里，禁止 inline 驱动连接代码。
- `api/core/security.py`：最简 JWT（HS256），单管理员账号从环境变量读（`ADMIN_USERNAME`/`ADMIN_PASSWORD`）。**自用内网场景，不做 RBAC**——需要分角色时先在方案文档立项再实现。
- `api/core/exceptions.py`：全局异常兜底（500 统一 `{"detail": "服务器内部错误"}`，HTTPException 保持默认契约）。
- `api/middleware/`：操作日志中间件。
- `scheduler/`：APScheduler 定时任务，任务体只编排，逻辑放 `models/`/`data/`。

## 2. 路由规范（核心）

- 路由只做**编排**：pydantic 参数校验 → 调 `models/`/`data/` → 组装响应。**业务/算法逻辑禁止写在路由里**。
- 输入输出一律 pydantic 模型（定义在 `api/schemas/`），字段与方案输入输出规范（如 §4.1.5）**逐字段对齐**；单位写进 Field description（`℃`、`t`、`%`）。
- 下游依赖（算法模块、数据库）一律函数体内延迟 import + `ImportError → 503`（现状模式），未接通的功能返回 `503 + 明确 detail`，**禁止静默返回空数据或假数据**。
- 健康检查 `/health`：依赖不可达报 `degraded`，不抛 500。
- 错误格式统一 `{"detail": "中文错误描述"}`；语义：401 认证失败 / 422 参数非法 / 503 依赖未就绪 / 404 资源不存在。
- 无全局前缀，各 router 自带前缀（`/blend`、`/furnace`……），与 `docs/API文档.md` 保持一致。

## 3. 安全与审计

- 所有写操作（POST/PUT/DELETE）必须过操作日志中间件：记录用户/IP/方法/路径/状态码/耗时，**不记录请求体**（防泄密）。
- 连接串、密钥只从环境变量读，日志中输出连接信息必须脱敏。
- 涉及控制下发的接口（如 `/furnace/control-mode`、`/furnace/ai-setpoint`）：AI 设定值必须先过 `models/furnace_control/safety_limits.py` 的 `clamp_*` 再返回/下发（方案§4.2.6 红线，不得绕过）。

## 4. 定时任务规范（scheduler/）

- 任务注册集中在 `jobs.py`：每日 PdM 趋势预测、数据质量日报、每周模型重训触发。
- **文档说后置的任务只许注释列出、不许注册**（现状：RUL 任务，方案§4.3）。
- 任务体必须可重入（失败重跑不产生脏数据）；长任务加锁防并发重入。
- `worker.py` 常驻进程须处理 SIGINT/SIGTERM 优雅停机。

## 5. 变更联动（后端特有）

- 新增/修改接口 → 同步 `docs/API文档.md` + 受影响的前端 README + `tests/integration/`（总纲 §0.3 对照表）。
- 接口字段与表结构相关时 → 先查 `data/schemas/postgresql.sql` 与方案§3.4 是否也要动。
