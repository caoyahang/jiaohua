/**
 * PdM 通用展示件：状态/优先级/ISO 分区徽标与文字映射。
 * 颜色一律取自 src/styles/tokens.ts（红线4），组件内不写颜色字面量。
 */
import { Tag } from 'antd';
import { colors } from '../styles/tokens';
import { PDM_DEVICE_REGISTRY } from '../api/mock';
import type { AlarmLevel, AlarmSource, DevicePriority, DeviceStatus, VibrationZone } from '../api/types';

/** 运行状态 → 中文文案与 token 颜色 */
const STATUS_META: Record<DeviceStatus, { text: string; color: string }> = {
  running: { text: '运行', color: colors.success },
  stopped: { text: '停机', color: colors.textSecondary },
  maintenance: { text: '检修', color: colors.warning },
  fault: { text: '故障', color: colors.danger },
};

/** ISO 10816 分区 → token 颜色（良好绿/注意黄/不合格橙/危险红） */
const ZONE_COLOR: Record<VibrationZone, string> = {
  良好: colors.success,
  注意: colors.warning,
  不合格: colors.orange,
  危险: colors.danger,
};

/** 优先级 → token 颜色（P0 最重要） */
const PRIORITY_COLOR: Record<DevicePriority, string> = {
  P0: colors.danger,
  P1: colors.warning,
  P2: colors.info,
};

/** 告警级别 → token 颜色 */
const LEVEL_COLOR: Record<AlarmLevel, string> = {
  WARNING: colors.warning,
  DANGER: colors.danger,
};

/** 告警来源 → 中文文案（方案§4.3.2 两级预警） */
const SOURCE_TEXT: Record<AlarmSource, string> = {
  level1_anomaly: '实时异常',
  level2_trend_forecast: '趋势预测',
};

export const statusTag = (s: DeviceStatus) => (
  <Tag color={STATUS_META[s].color}>{STATUS_META[s].text}</Tag>
);

export const zoneTag = (z: VibrationZone) => <Tag color={ZONE_COLOR[z]}>{z}</Tag>;

export const priorityTag = (p: DevicePriority) => <Tag color={PRIORITY_COLOR[p]}>{p}</Tag>;

export const levelTag = (l: AlarmLevel) => (
  <Tag color={LEVEL_COLOR[l]}>{l === 'WARNING' ? '预警' : '危险'}</Tag>
);

export const sourceText = (s: AlarmSource) => SOURCE_TEXT[s];

/** device_id → 设备名（注册清单与后端 pdm.py 逐字一致）；未知 id 原样返回 */
export function deviceNameOf(deviceId: string): string {
  return PDM_DEVICE_REGISTRY.find((d) => d.device_id === deviceId)?.name ?? deviceId;
}

/** device_id → 优先级；未知按 P2 处理（排序兜底） */
export function devicePriorityOf(deviceId: string): DevicePriority {
  return PDM_DEVICE_REGISTRY.find((d) => d.device_id === deviceId)?.priority ?? 'P2';
}
