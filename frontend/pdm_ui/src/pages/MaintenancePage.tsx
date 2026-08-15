/**
 * 检修计划页：由未确认告警自动生成检修建议（全部 mock 派生，恒挂演示数据角标）。
 * 建议检修日期：DANGER +3 天、WARNING +14 天；按优先级 P0→P2 排序。
 * 检修建议由两级告警自动生成，人工确认后执行（本界面不做自动派工）。
 */
import { useEffect, useState } from 'react';
import { Alert, Card, message, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { listAlarms } from '../api';
import { mockDeviceRuntime } from '../api/mock';
import type { AlarmLevel, DevicePriority, PdmAlarm } from '../api/types';
import MockBadge from '../components/MockBadge';
import { deviceNameOf, devicePriorityOf, priorityTag } from '../components/pdmTags';
import { useAlarmAckStore } from '../stores/alarmAck';

/** 检修建议行 */
interface MaintenanceRow {
  key: string;
  device_id: string;
  priority: DevicePriority;
  /** 建议内容 */
  suggestion: string;
  /** 触发告警消息 */
  alarm_msg: string;
  level: AlarmLevel;
  last_maintenance_date: string;
  /** 建议检修日期 YYYY-MM-DD */
  suggested_date: string;
}

/** 按告警级别/来源生成建议内容 */
function suggestionOf(alarm: PdmAlarm): string {
  if (alarm.level === 'DANGER') {
    return alarm.source === 'level1_anomaly'
      ? '立即安排停机检查，排除实时异常后再投入运行'
      : '趋势预测即将超限，3 天内安排停机检修';
  }
  return alarm.source === 'level1_anomaly'
    ? '安排现场点检，核实传感器读数与设备状态'
    : '纳入下次计划检修，持续观察趋势变化';
}

/** 建议检修日期：DANGER +3 天，WARNING +14 天 */
function suggestedDateOf(alarm: PdmAlarm): string {
  const days = alarm.level === 'DANGER' ? 3 : 14;
  return new Date(new Date(alarm.ts).getTime() + days * 86400_000)
    .toISOString()
    .slice(0, 10);
}

const PRIORITY_ORDER: Record<DevicePriority, number> = { P0: 0, P1: 1, P2: 2 };

export default function MaintenancePage() {
  const [rows, setRows] = useState<MaintenanceRow[]>([]);
  const [mock, setMock] = useState(false);
  const [loading, setLoading] = useState(false);
  const acks = useAlarmAckStore((s) => s.acks);

  useEffect(() => {
    setLoading(true);
    listAlarms()
      .then((resp) => {
        setMock(resp.__mock === true);
        // 只取未确认告警生成建议；已确认的由人工按处置意见执行
        const pending = resp.alarms.filter((a) => !a.acknowledged && !(a.alarm_id in acks));
        const list = pending.map((a) => ({
          key: a.alarm_id,
          device_id: a.equipment_id,
          priority: devicePriorityOf(a.equipment_id),
          suggestion: suggestionOf(a),
          alarm_msg: a.msg,
          level: a.level,
          last_maintenance_date: mockDeviceRuntime(a.equipment_id).last_maintenance_date,
          suggested_date: suggestedDateOf(a),
        }));
        // 按优先级排序（同级 DANGER 优先）
        list.sort(
          (a, b) =>
            PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] ||
            (a.level === b.level ? 0 : a.level === 'DANGER' ? -1 : 1),
        );
        setRows(list);
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : '查询失败');
      })
      .finally(() => setLoading(false));
  }, [acks]);

  const columns: ColumnsType<MaintenanceRow> = [
    {
      title: '设备',
      dataIndex: 'device_id',
      width: 150,
      render: (v: string) => deviceNameOf(v),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 90,
      render: (v: DevicePriority) => priorityTag(v),
    },
    { title: '建议内容', dataIndex: 'suggestion' },
    { title: '触发告警', dataIndex: 'alarm_msg' },
    { title: '上次检修', dataIndex: 'last_maintenance_date', width: 110 },
    { title: '建议检修日期', dataIndex: 'suggested_date', width: 120 },
  ];

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        检修计划
        {mock && <MockBadge />}
      </h2>
      <Alert
        type="info"
        showIcon
        className="mb-3"
        message="检修建议由两级告警自动生成，人工确认后执行"
      />
      <Card size="small" title="检修建议（来自未确认告警）">
        <Table<MaintenanceRow>
          rowKey="key"
          size="small"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}
