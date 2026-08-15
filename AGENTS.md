# AGENTS.md — AI 书写与协作规范（焦化厂智能化平台）

> 本文件是 AI（及人）在本项目工作时的**强制规范**。目标：**文档驱动开发**——
> 文档定义契约，代码实现契约；任何变更双向联动、可通过锚点定位。
> 阅读顺序：本文件 → `docs/requirements/AI焦化厂智能化落地方案_V1.1.md`（顶层需求）→ `docs/` 四份契约文档 → 代码。
> 全部文档的索引与版本管理规则见 `docs/README.md`（文档地图）。

---

## 0. 文档驱动总原则（最高优先级）

### 0.1 单一事实来源（SSOT）分层

| 层级 | 文件 | 管什么 |
|---|---|---|
| L1 顶层需求 | `docs/requirements/AI焦化厂智能化落地方案_V1.1.md`（旧版在 `docs/requirements/archive/`） | 业务目标、算法选型、KPI、阶段路线、安全红线 |
| L2 契约文档 | `docs/数据接口规范.md`、`docs/模型说明文档.md`、`docs/API文档.md`、`docs/操作手册.md` | 接口/表结构/模型/运维的**对外契约** |
| L3 配置 | `config/settings.yaml`、`config/dcs_tags.yaml`、`config/model_config.yaml` | 阈值、点位、超参的**唯一存放处** |
| L4 代码 | `data/`、`models/`、`services/` | 契约的实现，不得自创口径 |

**铁律**：同一个事实只允许存在一个权威定义。代码里的常量若与 L1~L3 冲突，以文档/配置为准改代码；若发现文档本身错了，**先改文档再改代码**，并在文档修订记录中留痕。

### 0.2 锚点机制（方便定位更改）

- 文档章节号为锚点：写作 `方案§4.2.6`、`方案§10.1`。
- 每个代码文件的**文件头 docstring 必须标注其依据的锚点**（现状已如此，新增文件必须遵守），例如：
  ```python
  """换向期数据标记（方案§4.2.6 红线）。"""
  ```
- 文档中提到实现时**必须写代码路径**，例如：`实现见 data/pipeline/k_coefficients.py`。
- 提交信息/变更说明引用锚点：`fix(方案§4.1.5): 配比和校验容差改为1e-3`。

### 0.3 变更联动对照表（改一处，必查其余）

| 变更类型 | 必改 | 同步检查 |
|---|---|---|
| 新增/修改 API 接口 | `services/api/routes/*.py` | `docs/API文档.md`、受影响的前端 README、`tests/integration/` |
| 表结构（PostgreSQL） | `data/schemas/postgresql.sql` + `data/schemas/migrations/VNNN__*.sql` | 方案§3.4、`docs/数据接口规范.md`、相关路由/ETL 查询（迁移规则见 migrations/README.md） |
| 时序超级表（TDengine） | `data/schemas/tdengine.sql` | 方案§3.4、采集端写入字段、`config/dcs_tags.yaml` |
| DCS 点位 | `config/dcs_tags.yaml` | 采集客户端、方案§3.2.1 接口表、ETL 字段映射 |
| 阈值/判定口径 | `config/settings.yaml` | 方案§3.3/§10.1、使用该阈值的模块与单测 |
| 配煤特征（增删维度） | `data/pipeline/feature_store.py` | 方案§4.1.4、`docs/模型说明文档.md`、`blend_detail`/`coke_quality` 表结构、训练/预测代码 |
| 模型超参 | `config/model_config.yaml` | 对应 train.py、MLflow 实验记录 |
| KPI/验收口径 | 方案§10.1 | `docs/操作手册.md` 验收章节、相关单测断言 |
| 安全限值 | `models/furnace_control/safety_limits.py` | 方案§4.2.6、§9.1 第8条——**红线变更须人工评审，AI 不得自行修改** |
| 函数/类签名 | 定义处 | 全部调用点 + 对应单测（先改测试或同步改，禁止留 skip 搪塞） |

每次变更完成前自问：**对照表里的每一行都检查过了吗？**

### 0.4 文档修订留痕

- L1 方案文档：修订在文首「修订记录」追加条目（版本号 + 条目 + 章节号）。
- L2 契约文档：文末维护「变更记录」小节（日期 + 变更点 + 对应代码路径）。
- 禁止无声变更：代码改了契约而文档没动，视为**未完成的工作**。

---

## 1. 通用 Python 规范

- 编码 UTF-8；注释/docstring 用**中文**；标识符用英文 snake_case（函数/变量）、PascalCase（类）。
- 所有公共函数/类写 docstring：用途、Args、Returns、依据的方案锚点。
- 类型注解全覆盖（`from __future__ import annotations` 起步）。
- **重依赖懒加载**：torch / scikit-opt / shap / ultralytics / asyncua 等只允许在函数体内或 PEP 562 `__getattr__` 中导入——未装重依赖的环境也必须能 import 轻量模块、能跑单测（参照 `models/blending_optimizer/__init__.py`）。
- 不得引入方案§6.1 技术栈之外的依赖；确需新增先在 `pyproject.toml`（依赖唯一声明处）和方案§6.1 中登记。
- 半成品必须显式：`raise NotImplementedError` 或 `# TODO:` + 说明，**禁止用 `pass` 或假数据冒充完成**。
- 安全红线：`models/furnace_control/safety_limits.py` 的钳位不得绕过、不得"临时放宽"；AI 设定值必须先过 `clamp_*` 再出库/下发（方案§4.2.6）。

## 2. 分域书写规范（拆分为独立规则文件）

各代码目录下有专属 `AGENTS.md`，**在该目录工作时强制生效**（嵌套规范，深层优先）：

| 规则文件 | 适用目录 | 管什么 |
|---|---|---|
| `services/AGENTS.md` | `services/api/`、`services/scheduler/` | 后端：路由编排、pydantic 契约、错误语义、认证审计、定时任务 |
| `data/AGENTS.md` | `data/schemas/`、`data/collector/`、`data/pipeline/` | 数据库与数据层：PG/TDengine/Redis、采集、质量校验红线、特征与K系数 |
| `models/AGENTS.md` | `models/` | 模型/算法：接口统一、MLflow 纪律、可解释性、安全红线、后置纪律 |
| `frontend/AGENTS.md` | `frontend/` | 前端：自用从简、模块-接口对应、工艺人员设计纪律 |

**规则唯一存放**：每类规则只存在于对应分域文件中，本总纲不复制其内容；修改规则改对应文件，并在 `docs/README.md` 变更记录留痕。

## 3. 配置规范（`config/`）

- `settings.yaml`：运行参数与阈值；`dcs_tags.yaml`：点位映射；`model_config.yaml`：模型超参。三者职责不交叉。
- 配置里**禁止出现明文密码**——连接串从环境变量读（`.env`，样例见 `.env.example`）。
- 改阈值必须在值旁边写注释：依据（方案锚点或现场标定日期）。

## 4. 测试规范（`tests/`）

- 单测与**真实 API 签名**对齐：改了被测函数，同一次变更里改测试；禁止用 `pytest.importorskip`/`skip` 长期搪塞（跨板块未就绪时允许临时使用，就绪后必须补齐为真实断言）。
- 测试数据自己构造、可复现（参照现有三个 unit 文件风格）；断言要算得出期望值，禁止 `assert result is not None` 式空转。
- 红线的测试永不删除：换向窗口 2~3 分钟强校验、K3=K1×K2 恒等式、约束违反量口径。
- 提交前跑 `python -m pytest tests/ -q`，全绿才算完成。

## 5. 脚本/运维规范（`scripts/`）

- bash 脚本首行 `set -euo pipefail` + 中文注释；破坏性操作（清库、删备份）必须有人工确认开关。
- 部署/备份/重训只走脚本，不在文档里写"手动执行某条命令"作为正式流程。

---

## 附：AI 工作时的自检清单

每次交付前逐项确认：

1. 代码文件头有没有方案锚点？文档里有没有代码路径？
2. §0.3 对照表涉及的文件是否全部同步？
3. 有没有引入技术栈外依赖、明文密码、假实现？
4. 安全红线（safety_limits、换向窗口、DCS 硬联锁表述）有没有被碰？
5. 测试是否全绿？新增逻辑有没有对应测试？
6. 文档修订记录是否留痕？
