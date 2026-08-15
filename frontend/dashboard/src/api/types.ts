/**
 * 接口类型汇总（领导驾驶舱）。
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

// ---------- 安全视觉告警（GET /vision/alarms，占位 200 空表 → 识别降级 mock） ----------

/** 告警场景（方案§4.4.1，大屏只展示前四类人员/安全场景） */
export type VisionScene = 'helmet' | 'fire_smoke' | 'intrusion' | 'gas_leak';

export interface VisionAlarm {
  alarm_id: number;
  scene: VisionScene;
  /** 区域（如 1#焦炉炉顶） */
  area: string;
  camera_id: string;
  /** 置信度 0~1 */
  confidence: number;
  /** 告警时间 ISO 字符串 */
  ts: string;
  acknowledged: boolean;
}

export interface VisionAlarmsResponse {
  alarms: VisionAlarm[];
  /** 后端占位响应带 detail 提示（如「告警表待建」），用于识别降级 */
  detail?: string;
}

// ---------- PdM 告警（GET /pdm/alarms，占位 200 空表 → 识别降级 mock） ----------

export type PdmLevel = 'WARNING' | 'DANGER';

export interface PdmAlarm {
  alarm_id: number;
  equipment_id: string;
  level: PdmLevel;
  msg: string;
  ts: string;
  acknowledged: boolean;
}

export interface PdmAlarmsResponse {
  alarms: PdmAlarm[];
  detail?: string;
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
