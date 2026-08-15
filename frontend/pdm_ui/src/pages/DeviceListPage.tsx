/**
 * 设备总览页：GET /pdm/devices（注册信息真实可用）+ mock 运行字段。
 * 运行字段（状态/健康评分/振动/温度）后端未出，页面恒挂「演示数据」角标。
 * 点击设备名进入单机详情 /devices/:device_id。
 */
import { useEffect, useState } from 'react';
import { Card, message, Select, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Link } from 'react-router-dom';
import { listDevices } from '../api';
import type { DevicePriority, DeviceRow } from '../api/types';
import MockBadge from '../components/MockBadge';
import { priorityTag, statusTag, zoneTag } from '../components/pdmTags';

const PRIORITY_OPTIONS = [
  { value: '', label: '全部优先级' },
  { value: 'P0', label: 'P0（关键设备）' },
  { value: 'P1', label: 'P1（重要设备）' },
  { value: 'P2', label: 'P2（一般设备）' },
];

export default function DeviceListPage() {
  const [priority, setPriority] = useState('');
  const [devices, setDevices] = useState<DeviceRow[]>([]);
  const [mock, setMock] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    listDevices((priority || undefined) as DevicePriority | undefined)
      .then((resp) => {
        setDevices(resp.devices);
        setMock(resp.__mock === true);
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : '查询失败');
      })
      .finally(() => setLoading(false));
  }, [priority]);

  const columns: ColumnsType<DeviceRow> = [
    {
      title: '设备名',
      dataIndex: 'name',
      render: (v: string, row) => (
        <Link to={`/devices/${row.device_id}`}>{v}</Link>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 90,
      render: (v: DevicePriority) => priorityTag(v),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: statusTag,
    },
    {
      title: '健康评分',
      dataIndex: 'health_score',
      width: 100,
      sorter: (a, b) => a.health_score - b.health_score,
    },
    {
      title: '振动速度 (mm/s)',
      dataIndex: 'vibration_speed',
      width: 140,
      render: (v: number) => v.toFixed(1),
    },
    {
      title: 'ISO 分区',
      dataIndex: 'vibration_zone',
      width: 110,
      render: zoneTag,
    },
    {
      title: '轴承温度 (℃)',
      dataIndex: 'bearing_temp',
      width: 120,
      render: (v: number) => v.toFixed(1),
    },
    { title: '上次检修', dataIndex: 'last_maintenance_date', width: 120 },
  ];

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        设备总览
        {mock && <MockBadge />}
      </h2>
      <Card
        size="small"
        title="监控设备清单（P0/P1/P2）"
        extra={
          <Select
            className="w-44"
            value={priority}
            options={PRIORITY_OPTIONS}
            onChange={setPriority}
          />
        }
      >
        <Table<DeviceRow>
          rowKey="device_id"
          size="small"
          loading={loading}
          columns={columns}
          dataSource={devices}
          pagination={false}
        />
      </Card>
    </div>
  );
}
