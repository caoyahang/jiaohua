# 模型/算法书写规范（models/）

> 适用范围：`models/` 全部算法模块（quality_predictor / blending_optimizer / furnace_control / pdm / vision / chemical_recovery）。
> 上位规范：根目录 `AGENTS.md`（文档驱动总原则 §0、通用 Python 规范 §1、变更联动对照表 §0.3）对本目录**强制生效**，本文件只补充算法专属规则。

## 1. 目录与接口

- 每个模型目录三件套：`train.py` / `predict.py` / `evaluate.py`（或方案文档明确豁免，如 `rul_estimator.py` 占位）。
- **接口统一**：经验模型与 ML 模型暴露相同的 `predict` 签名（参照 `quality_predictor/predict.py` 门面），冷启动→ML 的切换只允许改配置（`config/model_config.yaml`），**不许改调用方**。
- 重依赖（torch / scikit-opt / shap / ultralytics）按总纲 §1 懒加载：函数体内导入或 PEP 562 `__getattr__`（参照 `blending_optimizer/__init__.py`）——未装重依赖的环境也必须能 import 轻量模块、能跑单测。

## 2. 训练与上线纪律

- 训练必须过 MLflow 记录（参数/指标/数据版本）；模型上线走注册表，**禁止手拷 pkl 上线**。
- 增量学习（方案§4.1.7）：误差缓冲 → 阈值触发（50 条）→ `init_model` 热启动 + 小学习率（0.01）防遗忘；**上线前必须过回归验证闸门**——新模型在保留验证集上不回退才允许替换在线模型（见 `incremental.py` TODO，补实现时先补闸门）。
- 超参唯一来源 `config/model_config.yaml`，代码里不得出现第二份超参常量。

## 3. 可解释性（不是可选项）

- 配煤类输出必须附带 SHAP/边际贡献的**中文解释文本**（`blending_optimizer/explainer.py`）——"告诉配煤师为什么是这个配比"（方案§1.3 人在回路原则）。
- 老师傅能看懂的表述优先于技术精确性：解释文本里写"焦煤占比每降 1% 省 12 元、CSR 降 0.3%"，不写 SHAP 原始值堆砌。

## 4. 安全红线（furnace_control/）

- `safety_limits.py` 的钳位常量与 `clamp_*` 函数**不得绕过、不得"临时放宽"**；变更须人工评审并对照本厂 DCS 硬钳位组态（AI 包线 ≤ DCS 硬包线），同步方案§4.2.6 与 §9.1 第 8 条。
- 控制输出语义：AI 只输出设定值（setpoint）；联锁永远走 DCS 硬回路——代码注释中不得出现与此矛盾的表述。
- 影子模式（`shadow_mode.py`）必须完整记录 AI 推荐值 vs 人工操作值，这是影子→半自动→全自动切换的评审依据（方案§4.2.2）。

## 5. 后置纪律（文档说后置的，不许"顺手先做"）

- `pdm/rul_estimator.py`：仅占位。RUL 后置 2~3 年，故障样本 ≥50 例再立项（方案§4.3/§10.1）。
- `chemical_recovery/`：标"二期"，化产 OPC UA 数据积累 ≥3 个月后启动（方案§4.6）。
- 数字孪生：后置/可选，不在 `models/` 立项。

## 6. 变更联动（模型特有）

- 配煤特征增删 → 先改方案§4.1.4，再改 `data/pipeline/feature_store.py`，本目录训练/预测代码跟随（总纲 §0.3）。
- 模型行为变更（预测口径、解释口径）→ 同步 `docs/模型说明文档.md`。
- 改了公开函数签名 → 同一次变更内改全部调用点与对应单测，禁止留 skip 搪塞。
