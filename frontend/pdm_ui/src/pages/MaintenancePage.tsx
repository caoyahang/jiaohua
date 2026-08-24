/**
 * 检修计划页：由未确认告警自动生成检修建议（GET /pdm/alarms 真实查询，
 * 503/断网降级 mock 时挂演示数据角标）。
 * 建议检修日期：DANGER +3 天、WARNING +14 天；按级别 DANGER 优先排序。
 * 检修建议由两级告警自动生成，人工确认后执行（本界面不做自动派工）。
 *
 * 注：equipment_id 为 pdm_alarm 表 int 主键，设备表未建前无设备名/优先级映射，
 * 页面按编号展示；映射就绪后恢复设备名与优先级列。
 */
import { useEffect, useState } from 'react';
import { Alert, Card, message, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { listAlarms } from '../api';
import type { AlarmLevel, PdmAlarm } from '../api/types';
import MockBadge from '../components/MockBadge';
import { useAlarmAckStore } from '../stores/alarmAck';

/** 检修建议行 */
interface MaintenanceRow {
  key: number;
  equipment_id: number;
  /** 建议内容 */
  suggestion: string;
  /** 触发告警消息 */
  alarm_msg: string;
  level: AlarmLevel;
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

const LEVEL_ORDER: Record<AlarmLevel, number> = { DANGER: 0, WARNING: 1 };

/** 建议检修日期：DANGER +3 天，WARNING +14 天 */
function suggestedDateOf(alarm: PdmAlarm): string {
  const days = alarm.level === 'DANGER' ? 3 : 14;
  return new Date(new Date(alarm.ts).getTime() + days * 86400_000)
    .toISOString()
    .slice(0, 10);
}

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
        const pending = resp.items.filter((a) => !a.acknowledged && !(a.alarm_id in acks));
        const list = pending.map((a) => ({
          key: a.alarm_id,
          equipment_id: a.equipment_id,
          suggestion: suggestionOf(a),
          alarm_msg: a.msg ?? '',
          level: a.level,
          suggested_date: suggestedDateOf(a),
        }));
        // DANGER 优先（同级保持后端时间倒序）
        list.sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level]);
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
      dataIndex: 'equipment_id',
      width: 110,
      render: (v: number) => `设备 #${v}`,
    },
    { title: '建议内容', dataIndex: 'suggestion' },
    { title: '触发告警', dataIndex: 'alarm_msg' },
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
