/**
 * 接口类型汇总（运营总览，方案§7.2 阶段六）。
 *
 * 红线5：请求/响应类型优先来自 src/api/schema.d.ts（openapi-typescript 生成）。
 * 已知现实（前端规范§2.1）：furnace/pdm/vision 相关路由均未声明 response_model，
 * 生成的类型偏宽松不可用。以下类型以 services/api/routes/ 代码为准手写，
 * 待后端补 response_model 后改从 schema 引入。
 */
import type { components } from './schema';

// ---------- 来自 schema 的类型 ----------

export type TokenResponse = components['schemas']['TokenResponse'];

// ---------- 热工 K 系数（GET /furnace/k-coefficients，后端恒 503 → 必走 mock） ----------

/** 单班次 K 系数行（方案§4.2.6 统一考核口径，K3=K1×K2） */
export interface KCoefficientRow {
  furnace_id: number;
  /** 班次日期 YYYY-MM-DD */
  shift_date: string;
  /** 班次：早/中/晚 */
  shift: '早班' | '中班' | '晚班';
  /** K均：直行温度均匀系数 */
  k_uniform: number;
  /** K安：安定系数 */
  k_stable: number;
  /** K1 推焦计划系数 */
  k1: number;
  /** K2 推焦执行系数 */
  k2: number;
  /** K3 推焦总系数（=K1×K2） */
  k3: number;
}

export interface KCoefficientsResponse {
  coefficients: KCoefficientRow[];
}

// ---------- 安全视觉告警（GET /vision/alarms 真实查询 vision_alarm 表，503/断网降级 mock） ----------

/** 告警场景（docs/API文档.md §5 取值口径，方案§4.4.1） */
export type VisionScene = 'helmet' | 'fire' | 'intrusion' | 'gas_leak' | 'gauge' | 'coke_cake';

export interface VisionAlarm {
  alarm_id: number;
  scene: VisionScene;
  /** 区域（如 焦炉炉顶），可空 */
  area: string | null;
  camera_id: string;
  /** 检测类别（scene 的细粒度补充，如 flame/smoke），可空 */
  label: string | null;
  /** 置信度 0~1，可空 */
  confidence: number | null;
  /** 告警级别，可空 */
  level: string | null;
  msg: string | null;
  snapshot_url: string | null;
  acknowledged: boolean;
  /** 误报标记（回流训练集迭代） */
  is_false_positive: boolean;
  /** 告警时间 ISO 字符串 */
  ts: string;
}

export interface VisionAlarmsResponse {
  items: VisionAlarm[];
}

// ---------- PdM 告警（GET /pdm/alarms 真实查询 pdm_alarm 表，503/断网降级 mock） ----------

export type PdmLevel = 'WARNING' | 'DANGER';

export interface PdmAlarm {
  alarm_id: number;
  /** 设备主键（pdm_alarm.equipment_id，int） */
  equipment_id: number;
  level: PdmLevel;
  source: 'level1_anomaly' | 'level2_trend_forecast';
  metric: string | null;
  metric_value: number | null;
  threshold: number | null;
  iso10816_zone: string | null;
  msg: string | null;
  ts: string;
  acknowledged: boolean;
  handler: string | null;
  ack_comment: string | null;
  acked_at: string | null;
}

export interface PdmAlarmsResponse {
  items: PdmAlarm[];
}

// ---------- 全厂汇总 KPI（后端尚无聚合接口 → 固定 mock，角标常显） ----------

export interface OverviewKpi {
  /** 本月配煤成本节约（万元） */
  cost_saving_wan: number;
  /** 质量预测准确率（%） */
  quality_accuracy_pct: number;
  /** 煤气消耗（m³/h） */
  gas_consumption_m3h: number;
  /** 本月非计划停机（次） */
  unplanned_stops: number;
}

// ---------- 质量看板（后端无 coke_quality 查询接口 → 固定 mock） ----------
// 字段对齐 data/schemas/postgresql.sql coke_quality 表（m25/pred_m25 等）

export interface QualityBatch {
  batch_no: string;
  m25: number;
  pred_m25: number;
  m10: number;
  pred_m10: number;
  csr: number;
  pred_csr: number;
  cri: number;
  pred_cri: number;
}

export interface QualityBoardResponse {
  batches: QualityBatch[];
}

// ---------- 实时炉温（GET /furnace/temp，后端恒 503 → 必走 mock） ----------
// 字段口径与 furnace_ui 手写类型一致（TDengine furnace_temp 表，方案§3.4.3），
// 待后端补 response_model 后统一改从 schema 引入。

/** 燃烧侧：机侧 / 焦侧 */
export type BurnerSide = 'machine' | 'coke';

/** 控制模式三态（方案§4.2.2：manual 人工 / shadow 影子 / auto 自动） */
export type ControlMode = 'manual' | 'shadow' | 'auto';

/** GET /furnace/temp 时序点（TDengine furnace_temp 表字段口径，方案§3.4.3） */
export interface TempPoint {
  /** 采样时间 ISO 字符串 */
  ts: string;
  burner_side: BurnerSide;
  /** 火道温度 ℃ */
  fire_channel_temp: number;
  /** 煤气流量 m³/h */
  gas_flow: number;
  /** 烟道吸力 Pa */
  flue_suction: number;
  /** 集气管压力 Pa */
  collector_pressure: number;
  /** 废气残氧 % */
  oxygen_content: number;
  control_mode: ControlMode;
  /** 换向期标记：换向前后 2~3 分钟脏数据，不考核（方案§4.2.6） */
  switching: boolean;
}

/** GET /furnace/temp 响应（后端恒 503，前端必走 mock） */
export interface FurnaceTempResponse {
  furnace_id: number;
  points: TempPoint[];
}
