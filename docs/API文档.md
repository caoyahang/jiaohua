# API 文档

> AI焦化厂智能化平台后端接口（FastAPI，`services/api/`）。
> 本文档仅列出当前规划的接口清单，字段细节以实现代码（pydantic schema）为准。
> 无全局前缀，各路由自带前缀（`/blend`、`/furnace`、`/pdm`、`/vision`、`/auth`，见 `services/api/main.py`）；除 `/auth/login` 与 `/health` 外均需携带 JWT。

## 通用约定

- 认证：`POST /auth/login` 获取 Token，后续请求头携带 `Authorization: Bearer <token>`
- 错误格式：`{"detail": "错误描述"}`，HTTP 状态码遵循 REST 惯例
- 时间格式：ISO 8601（UTC+8）

---

## 1. 认证与健康检查

### POST /auth/login

用户登录，获取访问 Token。

**请求体**

```json
{
  "username": "operator01",
  "password": "******"
}
```

**响应**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### GET /health

服务健康检查（无需认证），供 docker-compose 健康检查与 Prometheus 探活使用。

**响应**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "dependencies": {
    "postgres": "ok",
    "tdengine": "ok",
    "redis": "ok"
  }
}
```

---

## 2. 智能配煤（blend）

### POST /blend/optimize

配煤方案优化：输入目标质量与可用煤种，返回三套方案（成本最优/质量最稳/综合推荐）。
对应 V1.1 §4.1.5 输入输出规范。

**请求体**

```json
{
  "target_quality": {
    "M25_min": 90.0,
    "M10_max": 6.5,
    "CSR_min": 65.0,
    "CRI_max": 25.0
  },
  "available_coals": [
    {
      "coal_id": 1,
      "name": "气煤-山西长治",
      "stock_tons": 5000,
      "price_per_ton": 1200,
      "min_ratio": 0.05,
      "max_ratio": 0.20,
      "lab_data": {"Ad": 8.5, "Vdaf": 38.2, "St_d": 0.65, "G": 65, "Y": 12.0, "Rmax": 0.75}
    }
  ],
  "max_cost_per_ton": 1500,
  "priority": "cost"
}
```

`priority` 取值：`cost` / `quality` / `balanced`。

**响应**

```json
{
  "solutions": [
    {
      "type": "cost_optimal",
      "blend_ratio": {"气煤": 0.15, "肥煤": 0.25, "焦煤": 0.35, "瘦煤": 0.25},
      "estimated_cost": 1380.5,
      "predicted_quality": {"M25": 91.2, "M10": 6.1, "CSR": 66.8, "CRI": 23.5},
      "confidence": 0.92,
      "explanation": "SHAP分析显示焦煤占比每降1%可省12元但CSR降0.3%"
    },
    {"type": "quality_stable"},
    {"type": "balanced"}
  ],
  "model_version": "v1.3",
  "compute_time_ms": 850
}
```

性能要求：求解时间 < 5 秒（V1.1 §10.1）。

### GET /blend/recipes

查询历史配煤方案（`blend_recipe` 表，含执行记录回写）。

**查询参数**：`furnace_id`、`date_from`、`date_to`、`ai_generated`、`page`、`page_size`

**响应**

```json
{
  "total": 120,
  "items": [
    {
      "batch_no": "BL20260726-001",
      "furnace_id": 1,
      "production_date": "2026-07-26",
      "total_coal_tons": 1200.0,
      "estimated_cost_per_ton": 1380.5,
      "actual_cost_per_ton": 1392.0,
      "ai_generated": true,
      "approved_by": 12
    }
  ]
}
```

### POST /blend/feedback

配煤执行结果反馈回写：化验结果回来后回填实际质量与成本，驱动增量学习闭环（V1.1 §4.1.7）。

**请求体**

```json
{
  "batch_no": "BL20260726-001",
  "actual_quality": {"M25": 90.8, "M10": 6.3, "CSR": 66.1, "CRI": 24.0},
  "actual_cost_per_ton": 1392.0,
  "lab_operator": "张三"
}
```

**响应**

```json
{"status": "accepted", "pred_error": {"M25": 0.4, "CSR": 0.7}, "incremental_buffer_size": 17}
```

---

## 3. 焦炉加热控制（furnace）

### GET /furnace/temp

查询火道温度等时序数据（TDengine `furnace_temp` 超级表）。

**查询参数**：`furnace_id`（必填）、`burner_side`（`machine`/`coke`）、`start`、`end`、`interval`（聚合粒度，如 `1m`/`5m`）

**响应**

```json
{
  "furnace_id": 1,
  "points": [
    {
      "ts": "2026-07-26T09:55:00+08:00",
      "burner_side": "machine",
      "fire_channel_temp": 1215.3,
      "gas_flow": 8600.0,
      "flue_suction": 185.0,
      "collector_pressure": 95.0,
      "oxygen_content": 5.2,
      "control_mode": "ai_shadow"
    }
  ]
}
```

### GET /furnace/ai-setpoint

获取 AI 推荐设定值（影子/自动模式下由 MPC 每 2 个交换周期计算一次，V1.1 §4.2.4）。

**查询参数**：`furnace_id`（必填）

**响应**

```json
{
  "furnace_id": 1,
  "ts": "2026-07-26T09:55:00+08:00",
  "ai_setpoint_gas": 8550.0,
  "ai_setpoint_suction": 182.0,
  "predicted_temp_30min": [1216.1, 1216.8],
  "control_mode": "ai_shadow",
  "note": "影子模式下仅展示，不下发DCS"
}
```

### POST /furnace/control-mode

切换控制模式（V1.1 §4.2.2 三阶段）。⚠️ 「一键切手动」为 DCS 硬切换，不经过本接口；
本接口仅用于 manual → ai_shadow → ai_auto 的软切换，且需双人确认权限。

**请求体**

```json
{
  "furnace_id": 1,
  "target_mode": "ai_auto",
  "operator_id": 12,
  "confirm": true
}
```

`target_mode` 取值：`manual` / `ai_shadow` / `ai_auto`。

**响应**

```json
{"furnace_id": 1, "control_mode": "ai_auto", "switched_at": "2026-07-26T09:56:00+08:00"}
```

### GET /furnace/k-coefficients

查询热工/推焦 K 系数（V1.1 §4.2.6 统一口径）。

**查询参数**：`furnace_id`、`shift_date`、`shift`（班次）

**响应**

```json
{
  "furnace_id": 1,
  "shift_date": "2026-07-26",
  "shift": "早班",
  "k_uniform": 0.91,
  "k_stable": 0.88,
  "k1": 0.96,
  "k2": 0.94,
  "k3": 0.9024
}
```

K均目标 ≥ 0.90（V1.1 §10.1），K3 目标 ≥ 0.95（V1.1 §4.5.1）。

---

## 4. 设备预测性维护（pdm）

### GET /pdm/devices

查询监控设备清单（P0/P1/P2 分级，V1.1 §4.3.1）。

> 实现现状（2026-08-15）：设备台账表未建，当前为内存注册表（`services/api/routes/pdm.py` DEVICE_REGISTRY），
> 只回注册信息；`workshop`/`status`/健康/振动等运行字段待设备台账与健康评分链路接入后提供。
> 台账落库后 `device_id` 将切换为整型主键（届时同步修订本契约）。

**查询参数**：`priority`（`P0`/`P1`/`P2`）

**响应**

```json
{
  "devices": [
    {
      "device_id": "pusher_travel",
      "name": "推焦车走行机构",
      "priority": "P0",
      "sensors": ["vibration", "current", "temperature"]
    }
  ],
  "total": 7
}
```

### GET /pdm/devices/{device_id}/health

查询单台设备的健康评分明细（振动/温度/电流分项得分与趋势）。

> 实现现状（2026-08-15）：恒 503（健康评分模型未部署）；以下为目标契约。

**响应**

```json
{
  "equipment_id": 101,
  "health_score": 86.5,
  "subscores": {"vibration": 82.0, "bearing_temp": 90.0, "motor_current": 88.0},
  "trend_7d": [88.1, 87.6, 87.0, 86.9, 86.7, 86.6, 86.5]
}
```

### GET /pdm/alarms

查询 PdM 两级预警告警（V1.1 §4.3.2：`level` 为严重度，两级分类在 `source` 字段：
`level1_anomaly` 实时异常 / `level2_trend_forecast` 趋势分级）。

**查询参数**：`equipment_id`(int)、`level`（`WARNING`/`DANGER`）、`date_from`、`date_to`、`acknowledged`、`limit`(默认50)

**响应**

```json
{
  "items": [
    {
      "alarm_id": 5001,
      "equipment_id": 101,
      "level": "WARNING",
      "source": "level2_trend_forecast",
      "msg": "劣化趋势明显，建议安排检修",
      "ts": "2026-07-26T08:00:00+08:00",
      "acknowledged": false
    }
  ]
}
```

响应项另透传详情字段：`metric` / `metric_value` / `threshold` / `iso10816_zone` / `handler` / `ack_comment` / `acked_at`（均可空）。

---

## 5. 安全视觉（vision）

### GET /vision/alarms

查询视觉 AI 告警（安全帽/烟火/闯入/煤气泄漏等，V1.1 §4.4.1）。

**查询参数**：`scene`（`helmet`/`fire`/`intrusion`/`gas_leak`/`gauge`/`coke_cake`）、`area`、`date_from`、`date_to`、`acknowledged`

**响应**

```json
{
  "items": [
    {
      "alarm_id": 9001,
      "scene": "helmet",
      "area": "焦炉炉顶",
      "camera_id": "CAM-T01",
      "snapshot_url": "/static/snapshots/9001.jpg",
      "confidence": 0.94,
      "ts": "2026-07-26T09:10:00+08:00",
      "acknowledged": false
    }
  ]
}
```

响应要求：识别到告警端到端 < 5 秒（V1.1 §10.1）。
响应项另透传详情字段：`label`（检测类别，scene 的细粒度补充）/ `level` / `msg` / `is_false_positive`（均可空）。

### POST /vision/alarms/{alarm_id}/ack

告警确认：记录处理人与处置意见；误报标记回流训练集迭代（V1.1 §4.4.1 每周重训消费）。
重复确认或告警不存在返回 404。

**请求体**

```json
{"handler": "张三", "comment": "已现场核实", "is_false_positive": false}
```

**响应**

```json
{"alarm_id": 9001, "status": "acked"}
```

---

## 6. 指标暴露

### GET /metrics

Prometheus 抓取端点（无需认证，仅容器网络内开放），配置见 `monitoring/prometheus/prometheus.yml`。
暴露：API 请求量/延迟、模型推理耗时、配煤求解耗时、PdM/vision 告警计数等自定义指标。

---

## 变更记录

| 日期 | 变更 | 对应代码路径 |
|---|---|---|
| 2026-08-15 | §5 告警接口对齐实现：`/pdm/alarms` 补 limit 参数与透传字段、明确 level/source 口径；`/vision/alarms` 补透传字段、新增 ack 小节；`/pdm/devices` 改为与代码一致的内存注册表现状（标注台账落库后切换整型主键）；`/pdm/devices/{id}/health` 标注 503 未部署 | `services/api/routes/pdm.py`、`services/api/routes/vision.py` |
