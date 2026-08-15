/**
 * 告警中心：两级预警列表（GET /pdm/alarms，10s 轮询）。
 * 后端真实可用但返回空占位（detail 含「待建」）→ 识别后降级 mock。
 *
 * TODO: 待后端补 PdM ack 接口。当前「确认」为前端本地状态（stores/alarmAck.ts），
 * 不落库；接口就绪后改为调用后端并回写。
 * 误报标记回流模型迭代：误报率是第一优先级指标，目标 <15%（方案§4.3）。
 */
import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Checkbox, Form, Input, message, Select, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useInterval } from 'ahooks';
import { listAlarms } from '../api';
import type { AlarmLevel, PdmAlarm } from '../api/types';
import ConfirmModal from '../components/ConfirmModal';
import MockBadge from '../components/MockBadge';
import { deviceNameOf, levelTag, sourceText } from '../components/pdmTags';
import { useAlarmAckStore } from '../stores/alarmAck';

const LEVEL_OPTIONS = [
  { value: '', label: '全部级别' },
  { value: 'WARNING', label: '预警（WARNING）' },
  { value: 'DANGER', label: '危险（DANGER）' },
];

interface AckForm {
  operator: string;
  opinion: string;
  false_positive: boolean;
}

export default function AlarmCenterPage() {
  const [level, setLevel] = useState('');
  const [alarms, setAlarms] = useState<PdmAlarm[]>([]);
  const [mock, setMock] = useState(false);
  const [loading, setLoading] = useState(false);
  // 待确认的告警（弹窗目标）
  const [target, setTarget] = useState<PdmAlarm | null>(null);
  const [form] = Form.useForm<AckForm>();
  const { acks, ackAlarm } = useAlarmAckStore();

  const fetchAlarms = useCallback(() => {
    setLoading(true);
    listAlarms((level || undefined) as AlarmLevel | undefined)
      .then((resp) => {
        setAlarms(resp.alarms);
        setMock(resp.__mock === true);
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : '查询失败');
      })
      .finally(() => setLoading(false));
  }, [level]);

  useEffect(fetchAlarms, [fetchAlarms]);
  // 告警页面刷新延迟 ≤10 秒（方案§7.2）：10s 轮询
  useInterval(fetchAlarms, 10_000);

  const onAck = async () => {
    if (!target) return;
    const values = await form.validateFields();
    ackAlarm(target.alarm_id, values);
    message.success('确认信息已记录（后端 PdM 确认接口待建）');
    setTarget(null);
    form.resetFields();
  };

  const isAcked = (a: PdmAlarm) => a.acknowledged || a.alarm_id in acks;

  const columns: ColumnsType<PdmAlarm> = [
    {
      title: '级别',
      dataIndex: 'level',
      width: 90,
      render: levelTag,
    },
    {
      title: '设备',
      dataIndex: 'equipment_id',
      width: 150,
      render: (v: string) => deviceNameOf(v),
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 100,
      render: sourceText,
    },
    { title: '消息', dataIndex: 'msg' },
    {
      title: '时间',
      dataIndex: 'ts',
      width: 170,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '确认状态',
      key: 'ack',
      width: 90,
      render: (_, row) => (isAcked(row) ? '已确认' : '未确认'),
    },
    {
      title: '操作',
      key: 'op',
      width: 90,
      render: (_, row) =>
        isAcked(row) ? (
          <span className="text-textSecondary">—</span>
        ) : (
          <Button size="small" type="link" onClick={() => setTarget(row)}>
            确认
          </Button>
        ),
    },
  ];

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        告警中心
        {mock && <MockBadge />}
      </h2>
      <Alert
        type="info"
        showIcon
        className="mb-3"
        message="误报请勾选「误报」标记，回流模型迭代——误报率是第一优先级指标，目标 <15%（方案§4.3）"
      />
      <Card
        size="small"
        title="两级预警列表（实时异常 / 趋势预测）"
        extra={
          <Select
            className="w-40"
            value={level}
            options={LEVEL_OPTIONS}
            onChange={setLevel}
          />
        }
      >
        <Table<PdmAlarm>
          rowKey="alarm_id"
          size="small"
          loading={loading}
          columns={columns}
          dataSource={alarms}
          pagination={{ pageSize: 10 }}
        />
      </Card>
      <ConfirmModal
        open={target !== null}
        title={`确认告警：${target ? deviceNameOf(target.equipment_id) : ''}`}
        okText="确认"
        onConfirm={onAck}
        onCancel={() => {
          setTarget(null);
          form.resetFields();
        }}
        content={
          <Form<AckForm> form={form} layout="vertical">
            <Form.Item
              name="operator"
              label="处理人"
              rules={[{ required: true, message: '请填写处理人' }]}
            >
              <Input placeholder="处理人姓名" />
            </Form.Item>
            <Form.Item
              name="opinion"
              label="处置意见"
              rules={[{ required: true, message: '请填写处置意见' }]}
            >
              <Input.TextArea rows={3} placeholder="现场检查情况与处置措施" />
            </Form.Item>
            <Form.Item name="false_positive" valuePropName="checked">
              <Checkbox>误报（标记后回流模型迭代）</Checkbox>
            </Form.Item>
          </Form>
        }
      />
    </div>
  );
}
