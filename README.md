# AI焦化厂智能化平台（coke_ai）

新建焦化厂（100万吨/年以上）的全栈 AI 智能化系统，覆盖**智能配煤、焦炉AI加热控制、设备预测性维护（PdM）、安全视觉AI、智能排产**五大应用，二期扩展**化产回收AI优化**。

核心理念：小步快跑、数据驱动、人机协同、闭环迭代。

> 本骨架依据《AI焦化厂智能化落地方案 V1.1》（`docs/requirements/`）搭建，文档索引见 `docs/README.md`。
> 开发/协作规范（文档驱动、变更联动对照表、各层书写规范）见 **`AGENTS.md`**——改代码前先读它。

## 总体目标（达产后12个月）

- 吨焦配煤成本降低 5~20 元
- 焦炭质量预测准确率 ≥ 90%（R² ≥ 0.85）
- 加热煤气消耗降低 ≥ 2.5%
- 非计划停机减少 ≥ 30%
- 安全 AI 识别覆盖率 100%，响应 < 5 秒
- 全厂数据在线率 ≥ 99%，延迟 ≤ 5 秒

## 目录结构

```
├── config/               # 全局配置 / DCS标签映射 / 模型超参
├── data/
│   ├── collector/        # OPC UA / Modbus / RTSP 采集
│   ├── pipeline/         # ETL / 数据质量校验（含换向期剔除）/ 特征仓库 / K系数
│   └── schemas/          # PostgreSQL + TDengine 建表 SQL + migrations/ 增量迁移
├── models/               # 算法层
│   ├── quality_predictor/    # 焦炭质量预测（经验模型冷启动 + LightGBM）
│   ├── blending_optimizer/   # 配煤优化（遗传算法）
│   ├── furnace_control/      # 焦炉加热控制（LSTM + MPC + 安全红线钳位）
│   ├── pdm/                  # 设备预测性维护（两级预警；RUL后置）
│   ├── vision/               # 视觉AI（YOLOv8）
│   ├── aps/                  # 智能排产（OR-Tools CP-SAT）
│   └── chemical_recovery/    # 化产回收优化（二期占位）
├── services/
│   ├── api/              # FastAPI 后端（routes 路由编排 / schemas pydantic契约 / db 连接层 / core 安全与异常 / middleware 操作日志）
│   └── scheduler/        # APScheduler 定时任务
├── frontend/             # 前端（React 18 + TS + AntD + ECharts，数字孪生后置）
├── monitoring/
│   ├── prometheus/       # prometheus.yml + rules/ 告警规则
│   └── grafana/          # dashboards/ 看板 JSON
├── logs/                 # 运行日志（gitignore）
├── docs/                 # 数据接口规范 / 模型说明 / 操作手册 / API文档
├── tests/                # 单元测试 + 集成测试
└── scripts/              # 部署 / 备份 / 模型重训 / 开发工具脚本（分类约定见 scripts/README.md）
```

## 快速启动

```bash
# 1. 配置环境变量
cp .env.example .env   # 修改 DB_PASSWORD 等

# 2. 启动数据底座（TDengine / PostgreSQL / Redis）
docker compose up -d tdengine postgres redis

# 3. 初始化数据库表结构
psql -h localhost -U ai_admin -d coke_plant -f data/schemas/postgresql.sql
taos -f data/schemas/tdengine.sql

# 4. 启动采集服务（对接 DCS 后）
python -m data.collector.opcua_client

# 5. 启动 API 服务
uvicorn services.api.main:app --host 0.0.0.0 --port 8000

# 6. 健康检查
curl http://localhost:8000/health
```

也可以直接使用 `make up` / `make init-db` / `make test`。

## 关键概念（V1.1）

### 经验模型冷启动

新厂无历史配煤数据，且同行配煤+化验数据属商业机密基本买不到。质量预测"模型A"投产前用**公开经验配煤模型**（CBRI法/新日铁配煤法/煤岩配煤模型）打底，配合 **40kg/200kg 试验焦炉 DOE 试验**（≥60炉，标定小炉与大炉 CSR/CRI 系统偏差）与 20~30 个拟采购煤种全分析数据库（含煤岩反射率分布）积累第一批自有数据；试生产数据达 200~500 组后切换 LightGBM。实现见 `models/quality_predictor/`，详见 `docs/模型说明文档.md` 第1节。

### 热工/推焦 K 系数（统一考核口径，V1.1 §4.2.6）

| 系数 | 定义 | 目标 |
|---|---|---|
| K均 | 直行温度均匀系数 =（机侧+焦侧合格火道数）/ 总测量火道数 | ≥ 0.90 |
| K安 | 直行温度安定系数（相邻班次标准温度波动合格率） | 热工稳定性考核 |
| K1 | 推焦计划系数（计划结焦时间与规定结焦时间符合率） | — |
| K2 | 推焦执行系数（实际推焦时间与计划时间符合率） | — |
| K3 | = K1 × K2，推焦总系数（排产核心KPI） | ≥ 0.95 |

计算见 `data/pipeline/`（K系数模块），查询接口 `GET /furnace/k-coefficients`。

### 化产回收 AI 优化（二期）

洗苯塔洗油温度/流量、饱和器母液酸度、鼓冷系统、脱硫液循环量寻优（LightGBM + 规则寻优）。接入条件：化产系统 OPC UA 数据积累 ≥3 个月后启动。代码占位见 `models/chemical_recovery/`，详见 `docs/模型说明文档.md` 第6节。

## 实施路线（V1.1 第7章）

1. **阶段一（M1~M2）数据底座**：Docker/TDengine/PostgreSQL/Redis、OPC UA 采集、数据质量校验（范围/突变/缺失插值）、建表、MLflow、FastAPI 基础框架。验收：采集延迟 ≤ 5秒、在线率 ≥ 99%
2. **阶段二（M2~M3）焦炭质量预测**：经验配煤模型（CBRI法/煤岩配煤法）冷启动打底；20~30个拟采购煤种全分析数据库（含煤岩反射率分布）；40kg/200kg 试验焦炉 DOE（≥60炉）并标定小炉与大炉 CSR/CRI 系统偏差；约40维特征（含炼焦工艺侧）；LightGBM 四指标 + SHAP。验收：DOE 数据集 R² ≥ 0.75
3. **阶段三（M3~M4）智能配煤优化器**：实时煤价/库存接入、遗传算法优化器、三套方案（成本最优/质量最稳/综合推荐）、约束处理、执行记录回写。验收：求解 < 5秒
4. **阶段四（M4~M6）焦炉AI加热控制**：LSTM 温度预测 + MPC（PSO求解）；**影子模式连续运行3个月**与人工对比；验证通过后 AI建议+人工确认 → 全自动（保留一键切手动）；安全联锁永远走 DCS 硬回路，AI 只输出 setpoint。验收：AI温控误差 < 人工误差、煤气消耗降 ≥ 2%
5. **阶段五（M5~M6）设备PdM + 安全视觉**：P0设备振动接入、孤立森林异常检测、LSTM趋势预测（ISO 10816分级）、YOLOv8 安全识别。验收：P0覆盖100%、告警响应 < 5秒
6. **阶段六（M6~M8）排产优化 + 领导驾驶舱**：OR-Tools CP-SAT 排产、K3系数自动计算、ECharts 平面大屏驾驶舱（数字孪生后置/可选）、移动端关键告警
7. **阶段七（M8~M12）闭环迭代**：自动重训管道、模型漂移检测、A/B测试、数据回流自动化、月度性能报告；二期启动化产回收AI优化（化产数据积累≥3个月后）

## 关键原则

- 数据 > 算法：采集与清洗投入占 60%
- 简单 > 复杂：LightGBM 能解决的绝不上深度学习
- 信任 > 精度：所有 AI 控制保留人工接管能力（一键切手动为硬切换）
- 安全红线：集气管压力高限等安全联锁永远走 DCS 硬联锁回路，AI 通道物理上无权触碰
