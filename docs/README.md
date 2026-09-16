# 文档地图（docs/README.md）

> 本项目全部 markdown 文档的索引、角色与版本管理规则。
> 规范细则见根目录 `AGENTS.md` §0（文档驱动总原则）；本文档是"找文档"的入口。

## 文档清单

### L1 顶层需求（requirements/）

| 文档 | 角色 | 状态 |
|---|---|---|
| `requirements/AI焦化厂智能化落地方案_V1.1.md` | 顶层方案：目标/KPI、算法选型、阶段路线、安全红线 | **当前有效** |
| `requirements/archive/AI焦化厂智能化落地方案_V1.0.md` | 初版方案（2026-07，评审前） | 归档，只读 |

### L2 契约文档（docs/ 根）

| 文档 | 契约内容 | 主要联动代码 |
|---|---|---|
| `数据接口规范.md` | 采集接口表、接口技术规格、数据治理标准、招采条款（方案§3.2/§3.3/§9.1） | `config/dcs_tags.yaml`、`data/collector/`、`data/schemas/` |
| `模型说明文档.md` | 六大 AI 应用与算法选型（方案§4/§5） | `models/`、`config/model_config.yaml` |
| `API文档.md` | 后端全部接口的请求/响应契约 | `services/api/routes/`、`frontend/` |
| `操作手册.md` | 阶段任务、验收标准、运维要点、Checklist（方案§7/§13） | `scripts/`、`services/scheduler/` |
| `进度跟踪.md` | 方案§7 七阶段**实际完成度**视图（✅/🚧/⬜ + 证据路径），随阶段级进展更新 | 全仓库 |

### L3 其他文档

| 文档 | 角色 |
|---|---|
| `../AGENTS.md` | AI 书写与协作**总纲**（强制）：文档驱动总原则、变更联动对照表、自检清单 |
| `../CLAUDE.md` | Claude Code 入口：导入 AGENTS.md/README.md + 终端调试速查（配 `.claude/settings.json` 权限白名单） |
| `../services/AGENTS.md` | 分域规则：后端（api/scheduler） |
| `../data/AGENTS.md` | 分域规则：数据库与数据层（schemas/collector/pipeline） |
| `../models/AGENTS.md` | 分域规则：模型/算法 |
| `../frontend/AGENTS.md` | 分域规则：前端 |
| `../README.md` | 项目门面：简介、快速启动、关键概念 |
| `../frontend/*/README.md` | 各前端模块的页面规划与接口对应关系 |
| `../monitoring/grafana/dashboards/README.md` | 仪表盘规划 |
| `配置与凭据管理.md` | 命令/环境变量/账号凭据的管理入口（只登记位置与影响面，不存真实密码） |

## 版本管理规则

1. **命名**：`名称_V主.次.md`。结构性/方向性变更升主版本，条目修订升次版本。
2. **当前版唯一**：`requirements/` 下只放当前有效版本；被替换的版本移入 `archive/` 并标注归档日期，**不删除**（评审结论与决策脉络要可追溯）。
3. **文首留痕**：每次修订在文首「修订记录」追加：版本号 + 日期 + 条目 + 章节号（参照 V1.1 的写法）。
4. **契约文档变更记录**：L2 四份文档在文末维护「变更记录」小节（日期 + 变更点 + 对应代码路径）。
5. **引用方式**：代码/配置中引用方案用书名《AI焦化厂智能化落地方案 V1.1》+ 章节号（§x.x.x），不写文件路径；文档之间引用写相对路径。
6. **同步义务**：任何文档变更若影响契约（接口/表结构/特征/阈值/KPI），必须按 `AGENTS.md` §0.3 对照表同步代码与其他文档，并在同一次变更中完成。

## 变更记录

| 日期 | 变更 | 说明 |
|---|---|---|
| 2026-07-26 | 文档归集管理 | 方案文档移入 `requirements/`，V1.0 归档至 `archive/`，建立本索引 |
| 2026-07-26 | 规范拆分 | 根 AGENTS.md 的分域规则拆至 services/ data/ models/ frontend/ 四个嵌套 AGENTS.md，根文件只保留总纲 |
| 2026-07-26 | 接入 Claude Code | 新增 `CLAUDE.md`（导入 AGENTS.md，不复制规则）+ `.claude/settings.json` 权限白名单 |
| 2026-08-15 | 前端四模块实现 | `frontend/` 四个模块建立 Vue3 工程并实现全部规划页面（blend_ui/furnace_ui/pdm_ui/dashboard）；统一 mock 降级约定（`blend_ui/src/api/client.js`）；各 README 接口清单以 routes 代码为准修正（`/pdm/equipment`→`/pdm/devices`、control-mode 请求体、dashboard 质量看板数据源改为固定 mock 待 coke_quality 接口） |
| 2026-08-15 | 前端技术栈切换 Vue→React+TS | 方案修订记录第 10 条（§6.1/§8.1）；`frontend/AGENTS.md` 重写：批准依赖清单（React18+TS+Vite+AntD5+Tailwind+styled-components+zustand+ahooks+echarts-for-react+overlayscrollbars+openapi-typescript+Playwright）+ 编码红线（单文件≤400行、逻辑样式分离、禁内联样式、颜色 token 化、接口类型由 OpenAPI 生成、新页面必配 Playwright 冒烟）；新增 `scripts/export_openapi.py` 与 `frontend/shared/openapi.json`；四模块同目录重建 |
| 2026-08-15 | 后端分层与架构预规划 | 方案修订记录第 11 条；`services/api/` 内部补 `core/`（security 迁入 + exceptions 全局兜底）、`db/connections.py`（连接层，路由不再 inline 驱动连接）、`schemas/`（pydantic 契约抽离）；新增 `data/schemas/migrations/`（编号增量 SQL + schema_migrations 追踪，`deploy.sh` 驱动）；依赖声明迁 `pyproject.toml`（requirements.txt 改为兼容 shim，新增 requirements-dev.txt）；monitoring 分 `prometheus/`（含 rules/）与 `grafana/dashboards/`；新增 `logs/`、`scripts/README.md`；OpenAPI 契约零变化（已 diff 验证） |
| 2026-08-15 | 建立 review 工序 | 仓库纳入 git（远程 origin=github.com/caoyahang/jiaohua）；新增 `scripts/check.sh` 评审门禁（pytest + 红线 grep + OpenAPI 契约新鲜度，`--full` 追加前端 tsc）+ Makefile `check`/`check-full` 目标 + pre-commit 钩子；`export_openapi.py` 增加 `--check` 模式；根 AGENTS.md §4 提交前要求改为 `make check` |
| 2026-08-15 | 新增进度跟踪文档 | `docs/进度跟踪.md`：首次全面盘点方案§7 七阶段实际完成度（状态 + 证据路径 + 缺口 + 下一步优先级）；本索引 L2 表同步登记 |
| 2026-08-15 | `/blend/optimize` 接通 + 文档清理 | `services/api/routes/blend.py` 装配优化器（经验模型冷启动，方案§4.1.6），新增 `tests/integration/test_blend_optimize.py`；删除根目录 `AI焦化厂落地方案.md`（与 `requirements/archive/` 已归档 V1.0 内容重复，违反 SSOT，git 历史可追溯）；`docs/进度跟踪.md` 同步 |
| 2026-08-15 | 新增配置与凭据管理文档 | `docs/配置与凭据管理.md`：`.env` 变量清单（含读取方与修改影响面）、Makefile/脚本/本地开发命令、部署前必改清单；遵循总纲§3（凭据只存 `.env`，文档不录真实值） |
| 2026-08-15 | 表结构补齐（方案修订12） | 方案§3.4.5~3.4.8 新增 coal/pdm_alarm/vision_alarm/operation_audit 四表 DDL；`data/schemas/postgresql.sql` 快照同步 + `migrations/V002__coal_alarm_audit_tables.sql`；`docs/进度跟踪.md` 同步 |
| 2026-08-15 | 告警/审计链路接入 + API文档§5 修正 | `/pdm/alarms`、`/vision/alarms` 真实查表，vision ack 落库；`middleware/operation_log.py` 写操作落 operation_audit；告警表口径按 API文档§5 修正（pdm level/source 分列、vision scene/area，vision 查询参数统一 `acknowledged`）；API文档§5 与代码不一致处修正（/pdm/devices 现状、health 503 标注、新增 ack 小节）并建立文末变更记录；前端 pdm_ui/dashboard 适配新契约（tsc + Playwright 过）；新增 `tests/integration/test_alarm_audit.py` |
| 2026-08-15 | 采集端 TDengine 写入落地 | `config/dcs_tags.yaml` 点位补落库映射字段（tag_key/furnace_id/burner_side，子表名=furnace{id}_{side}）；`data/collector/opcua_client.py` 实现 `build_tdengine_statements` + `write_to_tdengine`（范围检查拦截越限样本）；`docs/数据接口规范.md` §2/§5 同步并建立文末变更记录；新增 `tests/unit/test_opcua_tdengine.py` |
| 2026-08-16 | 驾驶舱大屏重设计 + 颜色 token 治理 | `frontend/dashboard` 按深色科技风重构：ScreenHeader（标题/时钟）、FurnaceSchematic（焦炉加热系统 SVG 示意，接 `/furnace/temp`，恒 503 走 mock）、Panel 统一面板壳、三栏网格布局；新色全部入 `darkColors` token；日志中间件 503 降噪（无库环境 DEBUG）；新增 `scripts/check_frontend_tokens.py`（base colors 四模块同源检查）并挂入 `check.sh`；frontend/AGENTS.md 红线4 补跨模块同源规则；同日二轮迭代：接入 DataV 组件库（方案修订13）、1920×1080 一屏自适应布局（flex + ResizeObserver 驱动 ECharts resize）、冒烟测试补 DataV 组件挂载断言 |
| 2026-08-16 | 驾驶舱接入 DataV 大屏组件库 | 方案修订记录第 13 条（§6.1）；`frontend/dashboard` 新增 `@jiaminghi/data-view-react@1.2.5`（批准清单登记于 frontend/AGENTS.md）：Panel 换 BorderBox12 科技边框、ScreenHeader 用 Decoration8 + 发光标题、KpiCards 数值换 DigitalFlop（千分位 formatter）、AlarmScrollList 换 ScrollBoard（DANGER 行 token 红高亮、悬停暂停自带）、整屏点阵纹理底（screen.styled.ts）；包无 TS 类型 → 本地声明 `src/types/data-view-react.d.ts`；颜色全部走 darkColors token |
| 2026-08-30 | P0 安全与部署首轮整改 | 安全设定值出口统一到 `models/furnace_control/safety_limits.py`（限值数值未改）；未完成的 AI setpoint/feedback 改为 503；控制模式强制双人确认且禁止 manual 软切换，前端安全写操作禁止 mock 成功；认证取消默认凭据、健康检查缺依赖改 degraded；Docker 构建上下文/认证注入修复并将未就绪 collector/trainer 隔离到 profile；同步 API/前端契约与回归测试 |
| 2026-08-30 | 全厂运营总览改版 | 方案修订记录第 14 条（§6.1/§7.2/§8.1）；`frontend/dashboard` 从深色 DataV 一屏驾驶舱改为浅色响应式运营管理页，移除 DataV 依赖、工艺 SVG 和告警轮播，保留 KPI/趋势/质量/安全告警及 10 秒轮询；同步 `frontend/AGENTS.md`、模块 README、操作手册、进度跟踪与 Playwright 冒烟测试 |
| 2026-09-16 | 数据质量日报统计落地 + 文档一致性收尾 | 新增 `data/pipeline/quality_report.py`（覆盖率/在线率/各标记计数统计，方案§3.3）+ `tests/unit/test_quality_report.py`；`services/scheduler/jobs.py` 日报任务接入统计函数并修正 `data_quality_report` 表待建的口径矛盾；`scripts/model_retrain.sh` 训练参数对齐 `train.py --config`（evaluate/anomaly_detect 无 CLI 标注 TODO）；修正远程地址大小写（Cyahang→caoyahang） |
| 2026-09-16 | 后端接口补 response_model（前后端契约强类型化） | 7 个已实现路由补齐响应契约：`/blend/optimize`、`/blend/recipes`、`/furnace/control-mode`、`/pdm/devices`、`/pdm/alarms`、`/vision/alarms`、`/vision/alarms/{id}/ack`；新建 `services/api/schemas/pdm.py`，blend/furnace/vision schema 追加响应模型；重新导出 `frontend/shared/openapi.json`。未实现路由（temp/ai-setpoint/k-coefficients/health/feedback）响应契约待定契约后补 |
| 2026-09-16 | 模型层规则补齐：懒加载整改 + 三件套 CLI | sko/shap 4 处函数体内懒加载（optimizer/mpc_controller/explainer/evaluate）；torch/ultralytics 改 PEP 562 包级懒加载（pdm/__init__.py、vision/__init__.py）；alarm_engine 的 redis/Detection 移 TYPE_CHECKING；evaluate.py/anomaly_detect.py 补 main + argparse；四个模型包未装重依赖均可轻量 import |
| 2026-09-16 | K 系数接口契约统一（消解前后端字段分歧） | `/furnace/k-coefficients` 响应定为班次记录列表 `{records: [...]}`（原 API 文档单对象示例不满足近 7 天趋势展示）；K均/K安字段名统一 `k_uniform`/`k_stable`（后端 `compute_all` 由 `k_jun`/`k_an` 更名）；补 `response_model`，重新导出 openapi.json 并四模块 gen:api；dashboard 的 `coefficients` 键名对齐为 `records` |




