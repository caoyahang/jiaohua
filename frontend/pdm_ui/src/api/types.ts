/**
 * 接口类型汇总（PdM 模块）。
 *
 * 红线5：请求/响应类型优先来自 src/api/schema.d.ts（openapi-typescript 生成）。
 * 已知现实（前端规范§2.1）：services/api/routes/pdm.py 三个接口均未声明
 * response_model，schema 中只有 paths 没有可用组件类型。以下类型以 pdm.py
 * 代码为准手写，待后端补 response_model 后改从 schema 引入并重新 gen:api。
 */
import type { components } from './schema';

// ---------- 来自 schema 的类型（后端模型字段完整，可直接用） ----------

export type LoginRequest = components['schemas']['LoginRequest'];
export type TokenResponse = components['schemas']['TokenResponse'];

// ---------- 手写类型（对应 pdm.py，待后端补 response_model 后改从 schema 引入） ----------

/** 设备优先级（pdm.py DEVICE_REGISTRY，方案§4.3.1 监控对象清单） */
export type DevicePriority = 'P0' | 'P1' | 'P2';

/** 设备运行状态（后端未出运行字段，由 mock 补齐） */
export type DeviceStatus = 'running' | 'stopped' | 'maintenance' | 'fault';

/** ISO 10816 振动分区（按振动速度有效值分级，边界 2.3/4.5/7.1 mm/s） */
export type VibrationZone = '良好' | '注意' | '不合格' | '危险';

/** 设备注册信息（GET /pdm/devices 真实响应元素） */
export interface PdmDevice {
  device_id: string;
  name: string;
  priority: DevicePriority;
  sensors: string[];
}

/** 设备运行字段（后端未出，mock 补齐，页面恒挂演示数据角标） */
export interface DeviceRuntime {
  status: DeviceStatus;
  /** 综合健康评分 0~100 */
  health_score: number;
  /** 振动速度有效值 mm/s */
  vibration_speed: number;
  /** ISO 10816 分区（由振动速度推得） */
  vibration_zone: VibrationZone;
  /** 轴承温度 ℃ */
  bearing_temp: number;
  /** 上次检修日期 YYYY-MM-DD */
  last_maintenance_date: string;
}

/** 设备总览行 = 注册信息（真实）+ 运行字段（mock 补齐） */
export type DeviceRow = PdmDevice & DeviceRuntime;

/** GET /pdm/devices 响应 */
export interface DevicesResponse {
  devices: PdmDevice[];
  total: number;
}

/** GET /pdm/devices/{device_id}/health 响应（后端恒 503，必走 mock） */
export interface HealthResponse {
  equipment_id: string;
  /** 综合健康评分 0~100 */
  health_score: number;
  /** 分项评分 0~100 */
  subscores: {
    vibration: number;
    bearing_temp: number;
    motor_current: number;
  };
  /** 近 7 天健康评分（旧→新） */
  trend_7d: number[];
}

/** 告警级别（两级预警体系，方案§4.3.2） */
export type AlarmLevel = 'WARNING' | 'DANGER';

/** 告警来源：level1 实时异常 / level2 趋势预测 */
export type AlarmSource = 'level1_anomaly' | 'level2_trend_forecast';

/** PdM 告警（GET /pdm/alarms 元素；后端返回空占位，必走 mock） */
export interface PdmAlarm {
  alarm_id: string;
  equipment_id: string;
  level: AlarmLevel;
  source: AlarmSource;
  msg: string;
  /** ISO 8601 时间戳 */
  ts: string;
  acknowledged: boolean;
}

/** GET /pdm/alarms 响应（detail 为占位说明，如「告警表待建」） */
export interface AlarmsResponse {
  alarms: PdmAlarm[];
  detail?: string;
}
