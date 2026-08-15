/**
 * 接口类型汇总（furnace_ui）。
 *
 * 红线5：请求/响应类型优先来自 src/api/schema.d.ts（openapi-typescript 生成）。
 * 已知现实（前端规范§2.1）：services/api/routes/furnace.py 未声明 response_model，
 * 响应类型以该文件代码为准在此手写，待后端补 response_model 后改从 schema 引入。
 */
import type { components } from './schema';

// ---------- 来自 schema 的类型（后端模型字段完整，可直接用） ----------

export type LoginRequest = components['schemas']['LoginRequest'];
export type TokenResponse = components['schemas']['TokenResponse'];
/** POST /furnace/control-mode 请求体（furnace.py ControlModeRequest） */
export type ControlModeRequest = components['schemas']['ControlModeRequest'];

// ---------- 手写类型（furnace.py 无 response_model，待后端补齐后改从 schema 引入） ----------

/** 控制模式三态（方案§4.2.2：manual 人工 / shadow 影子 / auto 自动） */
export type ControlMode = 'manual' | 'shadow' | 'auto';

/** 燃烧侧：机侧 / 焦侧 */
export type BurnerSide = 'machine' | 'coke';

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
export interface TempResponse {
  furnace_id: number;
  points: TempPoint[];
}

/** GET /furnace/ai-setpoint 响应（furnace.py 占位实现，真实可用） */
export interface AiSetpointResponse {
  furnace_id: number;
  /** AI 煤气流量设定值 m³/h（已过软件层 clamp_setpoint 钳位） */
  gas_flow_setpoint: number;
  /** 是否发生过安全钳位 */
  clamped: boolean;
  /** MLflow 模型版本；冷启动期为 null */
  model_version: string | null;
}

/** POST /furnace/control-mode 响应（真实可用） */
export interface ControlModeResponse {
  furnace_id: number;
  mode: string;
  status: string;
}

/** GET /furnace/k-coefficients 单班次记录（4.2.6 节统一考核口径） */
export interface KShiftRecord {
  furnace_id: number;
  /** 班次日期 YYYY-MM-DD */
  shift_date: string;
  /** 班次：早班 / 中班 / 晚班 */
  shift: string;
  /** K均：直行温度均匀系数（目标 ≥0.90） */
  k_uniform: number;
  /** K安：直行温度安定系数 */
  k_stable: number;
  /** K1：推焦计划系数 */
  k1: number;
  /** K2：推焦执行系数 */
  k2: number;
  /** K3：推焦总系数，恒等于 K1×K2（目标 ≥0.95） */
  k3: number;
}

/** GET /furnace/k-coefficients 响应（后端恒 503，前端必走 mock） */
export interface KCoeffResponse {
  records: KShiftRecord[];
}
