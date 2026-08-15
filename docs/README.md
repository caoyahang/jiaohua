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
| 2026-08-15 | 建立 review 工序 | 仓库纳入 git（远程 origin=github.com/Cyahang/jiaohua）；新增 `scripts/check.sh` 评审门禁（pytest + 红线 grep + OpenAPI 契约新鲜度，`--full` 追加前端 tsc）+ Makefile `check`/`check-full` 目标 + pre-commit 钩子；`export_openapi.py` 增加 `--check` 模式；根 AGENTS.md §4 提交前要求改为 `make check` |
