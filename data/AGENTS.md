# 数据库与数据层书写规范（data/）

> 适用范围：`data/schemas/`（建表 SQL）、`data/collector/`（采集）、`data/pipeline/`（ETL/质量校验/特征/K系数）。
> 上位规范：根目录 `AGENTS.md`（文档驱动总原则 §0、通用 Python 规范 §1、变更联动对照表 §0.3）对本目录**强制生效**，本文件只补充数据层专属规则。

## 1. PostgreSQL（业务数据，`schemas/postgresql.sql`）

- 建表/改表**只许改 schema 文件**，禁止在代码里拼 DDL；部署由 `scripts/deploy.sh` 幂等执行。
- **迁移机制**（`schemas/migrations/`，规则详见其 README）：`postgresql.sql` 是全量快照 SSOT；改表 = 改快照 + 新增 `VNNN__描述.sql` 增量（幂等）；deploy.sh 按序执行并记录 `schema_migrations` 表；已应用的 V 文件禁止修改。TDengine 超级表不走此机制。
- 命名：表名小写蛇形（`blend_recipe`），字段小写蛇形带单位语义（`ash`、`coking_time_hours`）。
- 类型约定：百分比/强度 `DECIMAL(5,2)`，硫分 `DECIMAL(6,3)`，配比 `DECIMAL(5,4)`，金额 `DECIMAL(10,2)`；分布/频谱类半结构化数据用 `JSONB`（如 `rmax_distribution`）并加 GIN 索引。
- 时间字段一律 `TIMESTAMP` 默认 `NOW()`；业务日期用 `DATE`。
- 改表必须同步（总纲 §0.3）：方案§3.4 + `docs/数据接口规范.md` + 受影响查询代码。

## 2. TDengine（时序数据，`schemas/tdengine.sql`）

- 每类时序一张**超级表**（`furnace_temp`、`vibration`），设备/炉号等维度进 TAGS，不进列。
- 写入字段与 `config/dcs_tags.yaml` 的 `tag_key` 一一对应；新增点位先改 tags 配置。
- **控制模式与 AI 推荐值必须随工艺值同行入库**（`control_mode`：manual/ai_shadow/ai_auto；`ai_setpoint_*`）——影子模式 AI vs 人工对比分析依赖它（方案§4.2.2），缺了就没法验收加热控制。

## 3. Redis

- 只放：热特征缓存、会话/控制模式、告警队列（`vision:alarms`）。key 带业务前缀 `模块:用途:ID`。
- 不存任何"丢了会出事"的数据——Redis 是缓存不是台账。

## 4. 采集规范（collector/）

- 点位唯一来源 `config/dcs_tags.yaml`；采集端**不得硬编码** node_id / 寄存器地址 / RTSP 地址。
- 断线重连、断点续传是硬性要求（方案§9.1 合同条款）：写采集代码时不留"断了就丢"的路径；恢复后按 history_read 补采缺口。
- 采集失败不得阻塞其他设备/点位的采集循环。
- 重依赖（asyncua/pymodbus/cv2）按总纲 §1 懒加载，未装 SDK 的环境也必须能 import 模块。

## 5. 质量校验红线（pipeline/quality_check.py）

- 所有入库时序数据**必经四道**：范围检查 → 突变检查 → 缺失插值 → **换向期标记**（前2后3分钟）。
- 换向窗口常量只允许在 2~3 分钟红线区间内（代码已强制 `ValueError`，方案§4.2.6），**禁止放宽**。
- 脏数据**打标记入库、建模前由 `filter_for_modeling` 剔除**，禁止直接丢弃——现场数据要可追溯。
- 突变点只打标记不置 NaN（可能是真实工况跳变），交由下游决策。

## 6. 特征与 K 系数（pipeline/feature_store.py、k_coefficients.py）

- 特征分组常量与方案§4.1.4 一一对应（约 40 维：单种煤基础 / 反射率分布 / 配比 / 成本 / 煤岩组合 / 工艺 / **炼焦工艺** / 约束）；增删维度先改方案§4.1.4 再改代码（总纲 §0.3）。
- K均/K安/K1/K2/K3 的判定口径与容差以 `config/settings.yaml` 的 `k_coefficients` 段为准，代码里不留第二份口径；空数据返回 NaN 由上游决定展示口径，禁止返回 0 冒充。
- K3 恒等式 `K3 = K1 × K2` 是永不删除的红线测试（`tests/unit/test_k_coefficients.py`）。
