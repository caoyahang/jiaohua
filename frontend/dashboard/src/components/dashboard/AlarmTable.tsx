/**
 * 最新视觉告警表格：展示时间、场景、区域、级别和确认状态。
 * 字段口径依据 docs/API文档.md §5 与方案§4.4.1。
 */
import { Table, Tag } from 'antd';
import type { TableColumnsType } from 'antd';
import type { VisionAlarm, VisionScene } from '../../api/types';

const SCENE_NAMES: Record<VisionScene, string> = {
  helmet: '未戴安全帽',
  fire: '烟火',
  intrusion: '区域闯入',
  gas_leak: '煤气泄漏',
  gauge: '表计读数异常',
  coke_cake: '焦饼成熟度异常',
};

/** 场景 → 中文名；接口出现新场景时原样回退展示。 */
export function sceneNameOf(scene: VisionScene): string {
  return SCENE_NAMES[scene] ?? scene;
}

const columns: TableColumnsType<VisionAlarm> = [
  {
    title: '时间',
    dataIndex: 'ts',
    width: 160,
    render: (value: string) => value.replace('T', ' ').slice(0, 19),
  },
  {
    title: '告警内容',
    dataIndex: 'scene',
    width: 150,
    render: (value: VisionScene) => sceneNameOf(value),
  },
  {
    title: '区域 / 相机',
    key: 'location',
    render: (_, row) => `${row.area ?? '未知区域'} / ${row.camera_id}`,
  },
  {
    title: '级别',
    dataIndex: 'level',
    width: 100,
    render: (value: string | null) => (
      <Tag color={value === 'DANGER' ? 'error' : 'warning'}>{value ?? 'WARNING'}</Tag>
    ),
  },
  {
    title: '状态',
    dataIndex: 'acknowledged',
    width: 100,
    render: (value: boolean) => (
      <Tag color={value ? 'default' : 'processing'}>{value ? '已确认' : '未确认'}</Tag>
    ),
  },
];

interface Props {
  alarms: VisionAlarm[];
}

export default function AlarmTable({ alarms }: Props) {
  return (
    <Table<VisionAlarm>
      rowKey="alarm_id"
      columns={columns}
      dataSource={alarms.slice(0, 10)}
      pagination={false}
      size="small"
      scroll={{ x: 760 }}
      locale={{ emptyText: '暂无视觉告警' }}
    />
  );
}
