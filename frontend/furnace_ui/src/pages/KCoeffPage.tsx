/**
 * K 系数看板页（README 接口清单：GET /furnace/k-coefficients 恒 503 → 必走 mock）。
 * K均/K安/K1/K2/K3 班次明细 + 近 7 天趋势；目标线：K均≥0.90、K3≥0.95（方案§4.2.6 统一考核口径）。
 */
import { useCallback, useState } from 'react';
import { Space, Table, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMount } from 'ahooks';
import type { EChartsOption } from 'echarts';
import { ApiError, getKCoefficients } from '../api';
import type { KShiftRecord } from '../api/types';
import { useFurnaceStore } from '../stores/furnace';
import ChartCard from '../components/ChartCard';
import MockBadge from '../components/MockBadge';
import { colors } from '../styles/tokens';

/** 低于目标值的 K 值红字加粗 */
function kCell(value: number, target: number) {
  const bad = value < target;
  return (
    <span className={bad ? 'text-danger font-bold' : undefined}>
      {value.toFixed(3)}
    </span>
  );
}

const COLUMNS: ColumnsType<KShiftRecord> = [
  { title: '日期', dataIndex: 'shift_date', key: 'shift_date' },
  { title: '班次', dataIndex: 'shift', key: 'shift' },
  {
    title: 'K均（≥0.90）',
    dataIndex: 'k_uniform',
    key: 'k_uniform',
    render: (v: number) => kCell(v, 0.9),
  },
  {
    title: 'K安',
    dataIndex: 'k_stable',
    key: 'k_stable',
    render: (v: number) => v.toFixed(3),
  },
  { title: 'K1', dataIndex: 'k1', key: 'k1', render: (v: number) => v.toFixed(3) },
  { title: 'K2', dataIndex: 'k2', key: 'k2', render: (v: number) => v.toFixed(3) },
  {
    title: 'K3（≥0.95）',
    dataIndex: 'k3',
    key: 'k3',
    render: (v: number) => kCell(v, 0.95),
  },
];

/** 近 7 天趋势折线：K均/K安/K3，红色 markLine 目标线 0.90/0.95 */
function buildTrendOption(records: KShiftRecord[]): EChartsOption {
  const labels = records.map((r) => `${r.shift_date.slice(5)} ${r.shift}`);
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['K均', 'K安', 'K3'] },
    grid: { left: 50, right: 20, top: 40, bottom: 60 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { interval: 2, rotate: 30 },
    },
    yAxis: { type: 'value', min: 0.7, max: 1 },
    series: [
      {
        name: 'K均',
        type: 'line',
        color: colors.primary,
        data: records.map((r) => r.k_uniform),
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: colors.danger, type: 'dashed' },
          label: { formatter: 'K均目标 0.90', color: colors.danger },
          data: [{ yAxis: 0.9 }],
        },
      },
      {
        name: 'K安',
        type: 'line',
        color: colors.success,
        data: records.map((r) => r.k_stable),
      },
      {
        name: 'K3',
        type: 'line',
        color: colors.warning,
        data: records.map((r) => r.k3),
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: colors.danger, type: 'dashed' },
          label: { formatter: 'K3目标 0.95', color: colors.danger },
          data: [{ yAxis: 0.95 }],
        },
      },
    ],
  };
}

export default function KCoeffPage() {
  const furnaceId = useFurnaceStore((s) => s.furnaceId);
  const [records, setRecords] = useState<KShiftRecord[]>([]);
  const [mock, setMock] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await getKCoefficients(furnaceId);
      setRecords(resp.records);
      setMock(resp.__mock === true);
    } catch (err) {
      if (err instanceof ApiError) message.error(err.message);
    } finally {
      setLoading(false);
    }
  }, [furnaceId]);

  useMount(load);

  return (
    <Space direction="vertical" size="middle" className="w-full">
      <Typography.Title level={4} className="m-0">
        热工 K 系数看板
        {mock && <MockBadge />}
      </Typography.Title>
      <ChartCard
        title="近 7 天 K 系数趋势（目标：K均≥0.90、K3≥0.95）"
        option={buildTrendOption(records)}
        height={320}
        mock={mock}
      />
      <Table<KShiftRecord>
        size="small"
        rowKey={(r) => `${r.shift_date}-${r.shift}`}
        columns={COLUMNS}
        dataSource={records}
        loading={loading}
        pagination={false}
        title={() => (
          <span>
            班次明细（K3=K1×K2，方案§4.2.6 考核口径）
            {mock && <MockBadge />}
          </span>
        )}
      />
    </Space>
  );
}
