/**
 * PdM 演示数据（mock）。
 *
 * 后端状态（services/api/routes/pdm.py）：
 * - GET /pdm/devices 真实可用，但响应只有注册信息 → 运行字段由本文件补齐
 * - GET /pdm/devices/{id}/health 恒 503 → 必走 mock
 * - GET /pdm/alarms 返回空占位（detail 含「待建」）→ 必走 mock
 *
 * 全部数据用种子化伪随机生成（种子 = device_id / 固定常量），
 * 保证 10s 轮询期间数值稳定、不跳变。
 */
import type {
  AlarmLevel,
  AlarmSource,
  DeviceRow,
  DeviceRuntime,
  DeviceStatus,
  HealthResponse,
  PdmAlarm,
  PdmDevice,
  VibrationZone,
} from './types';

/** 设备注册清单：与 pdm.py DEVICE_REGISTRY 逐字一致（方案§4.3.1），页面展示设备名用 */
export const PDM_DEVICE_REGISTRY: PdmDevice[] = [
  { device_id: 'pusher_travel', name: '推焦车走行机构', priority: 'P0', sensors: ['vibration', 'current', 'temperature'] },
  { device_id: 'guide_grid', name: '拦焦车导焦栅', priority: 'P0', sensors: ['vibration', 'displacement'] },
  { device_id: 'cdq_fan', name: '干熄焦循环风机', priority: 'P0', sensors: ['vibration_spectrum', 'bearing_temp'] },
  { device_id: 'coal_screw', name: '装煤车螺旋给料', priority: 'P1', sensors: ['current', 'rpm'] },
  { device_id: 'gas_blower', name: '焦炉煤气鼓风机', priority: 'P1', sensors: ['vibration', 'bearing_temp', 'flow'] },
  { device_id: 'chem_pump', name: '化产离心泵', priority: 'P1', sensors: ['vibration', 'seal_temp'] },
  { device_id: 'belt_conveyor', name: '皮带输送机', priority: 'P2', sensors: ['vibration', 'belt_deviation'] },
];

/** 字符串哈希（种子来源） */
function hashSeed(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** mulberry32 种子化伪随机数发生器 */
function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** ISO 10816 分区：由振动速度有效值推得（边界 2.3/4.5/7.1 mm/s） */
export function zoneOf(speed: number): VibrationZone {
  if (speed >= 7.1) return '危险';
  if (speed >= 4.5) return '不合格';
  if (speed >= 2.3) return '注意';
  return '良好';
}

const STATUS_POOL: DeviceStatus[] = ['running', 'running', 'running', 'stopped', 'maintenance', 'fault'];

/** 单台设备运行字段（纯种子决定，轮询期间稳定） */
export function mockDeviceRuntime(deviceId: string): DeviceRuntime {
  const rand = mulberry32(hashSeed(deviceId));
  const status = STATUS_POOL[Math.floor(rand() * STATUS_POOL.length)];
  // 振动速度 0.5~9.5 mm/s，覆盖 ISO 四区
  const vibrationSpeed = Math.round((0.5 + rand() * 9) * 10) / 10;
  // 健康评分与振动分区负相关：分区越差分越低
  const zonePenalty = { 良好: 0, 注意: 15, 不合格: 35, 危险: 55 }[zoneOf(vibrationSpeed)];
  const healthScore = Math.round(Math.min(100, Math.max(5, 95 - zonePenalty + (rand() - 0.5) * 10)));
  const bearingTemp = Math.round((42 + rand() * 40) * 10) / 10;
  // 上次检修：5~90 天前（按今天推，日期粒度天然稳定）
  const lastDate = new Date(Date.now() - (5 + Math.floor(rand() * 86)) * 86400_000);
  return {
    status,
    health_score: healthScore,
    vibration_speed: vibrationSpeed,
    vibration_zone: zoneOf(vibrationSpeed),
    bearing_temp: bearingTemp,
    last_maintenance_date: lastDate.toISOString().slice(0, 10),
  };
}

/** 设备总览 mock：注册信息 + 运行字段 */
export function mockDevices(): { devices: DeviceRow[]; total: number } {
  const devices = PDM_DEVICE_REGISTRY.map((d) => ({ ...d, ...mockDeviceRuntime(d.device_id) }));
  return { devices, total: devices.length };
}

/** 设备健康评分 mock（对应恒 503 的 /pdm/devices/{id}/health） */
export function mockHealth(deviceId: string): HealthResponse {
  const rand = mulberry32(hashSeed(`${deviceId}#health`));
  const runtime = mockDeviceRuntime(deviceId);
  const clampScore = (v: number) => Math.round(Math.min(100, Math.max(5, v)));
  const trend: number[] = [];
  // 7 天趋势：从今天往回推，围绕当前评分小幅波动
  for (let i = 6; i >= 0; i -= 1) {
    trend.push(clampScore(runtime.health_score + (rand() - 0.5) * 8 + i * (rand() - 0.6)));
  }
  trend[6] = runtime.health_score;
  return {
    equipment_id: deviceId,
    health_score: runtime.health_score,
    subscores: {
      vibration: clampScore(runtime.health_score + (rand() - 0.5) * 20),
      bearing_temp: clampScore(runtime.health_score + (rand() - 0.5) * 20),
      motor_current: clampScore(runtime.health_score + (rand() - 0.5) * 20),
    },
    trend_7d: trend,
  };
}

/** 告警 mock：6 条两级预警（方案§4.3.2），设备名取自注册清单 */
export function mockAlarms(): { alarms: PdmAlarm[] } {
  const rand = mulberry32(hashSeed('pdm-alarms'));
  const specs: { device: number; level: AlarmLevel; source: AlarmSource; msg: string }[] = [
    { device: 0, level: 'DANGER', source: 'level1_anomaly', msg: '振动速度 8.2 mm/s，进入 ISO 10816 危险区，建议立即检查' },
    { device: 2, level: 'DANGER', source: 'level2_trend_forecast', msg: '轴承温度 7 天持续上升，趋势预测 3 天内超温' },
    { device: 1, level: 'WARNING', source: 'level1_anomaly', msg: '导焦栅位移传感器读数异常波动' },
    { device: 4, level: 'WARNING', source: 'level2_trend_forecast', msg: '振动速度趋势上行，已进入 ISO 10816 注意区' },
    { device: 3, level: 'WARNING', source: 'level1_anomaly', msg: '电机电流短时超限（超额定值 12%）' },
    { device: 5, level: 'WARNING', source: 'level2_trend_forecast', msg: '密封温度缓慢爬升，建议安排计划检修' },
  ];
  const alarms = specs.map((s, i) => {
    const d = PDM_DEVICE_REGISTRY[s.device];
    return {
      alarm_id: `pdm-${d.device_id}-${String(i + 1).padStart(3, '0')}`,
      equipment_id: d.device_id,
      level: s.level,
      source: s.source,
      msg: s.msg,
      // 近 24 小时内，种子决定分钟偏移（刷新时分钟级漂移可接受）
      ts: new Date(Date.now() - Math.floor(rand() * 1440) * 60_000).toISOString(),
      acknowledged: false,
    };
  });
  // 按时间倒序，与后端约定一致
  alarms.sort((a, b) => (a.ts < b.ts ? 1 : -1));
  return { alarms };
}

/** 近 7 天振动速度趋势 mock（旧→新，mm/s）：围绕当前速度种子化波动，末点为当前值 */
export function mockVibrationTrend(deviceId: string): number[] {
  const rand = mulberry32(hashSeed(`${deviceId}#vibration-trend`));
  const current = mockDeviceRuntime(deviceId).vibration_speed;
  const trend: number[] = [];
  for (let i = 6; i >= 0; i -= 1) {
    const v = current + (rand() - 0.5) * 1.2 - i * (rand() - 0.55);
    trend.push(Math.round(Math.max(0.2, v) * 10) / 10);
  }
  trend[6] = current;
  return trend;
}
