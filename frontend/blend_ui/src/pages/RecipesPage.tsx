/**
 * 历史方案页：配煤方案查询（炉号筛选）+ AI 方案 vs 人工成本对比折线图。
 * GET /blend/recipes 依赖 PostgreSQL，不可用时 503 自动降级 mock。
 */
import { useEffect, useState } from 'react';
import { Card, Col, message, Row, Select, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { EChartsOption } from 'echarts';
import { listRecipes } from '../api';
import type { BlendRecipe } from '../api/types';
import ChartCard from '../components/ChartCard';
import MockBadge from '../components/MockBadge';

const FURNACE_OPTIONS = [
  { value: 0, label: '全部炉号' },
  { value: 1, label: '1 号炉' },
  { value: 2, label: '2 号炉' },
];

export default function RecipesPage() {
  const [furnaceId, setFurnaceId] = useState(0);
  const [recipes, setRecipes] = useState<BlendRecipe[]>([]);
  const [mock, setMock] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    listRecipes(furnaceId || undefined)
      .then((resp) => {
        setRecipes(resp.recipes);
        setMock(resp.__mock === true);
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : '查询失败');
      })
      .finally(() => setLoading(false));
  }, [furnaceId]);

  const columns: ColumnsType<BlendRecipe> = [
    { title: '批次号', dataIndex: 'batch_no', width: 160 },
    { title: '生产日期', dataIndex: 'production_date', width: 110 },
    { title: '炉号', dataIndex: 'furnace_id', width: 70, render: (v: number) => `${v} 号炉` },
    { title: '总煤量 (吨)', dataIndex: 'total_coal_tons', width: 110 },
    { title: '预估成本 (元/吨)', dataIndex: 'estimated_cost_per_ton', width: 130 },
    {
      title: '实际成本 (元/吨)',
      dataIndex: 'actual_cost_per_ton',
      width: 130,
      render: (v: number | null) => v ?? '—',
    },
    {
      title: '方案来源',
      dataIndex: 'ai_generated',
      width: 100,
      render: (v: boolean) =>
        v ? <Tag color="processing">AI</Tag> : <Tag>人工</Tag>,
    },
    {
      title: '审批人',
      dataIndex: 'approved_by',
      render: (v: string | null) => v ?? '—',
    },
  ];

  // AI vs 人工成本对比：按日期聚合两类方案的平均实际成本
  const byDate = new Map<string, { ai: number[]; manual: number[] }>();
  for (const r of recipes) {
    if (r.actual_cost_per_ton === null) continue;
    const bucket = byDate.get(r.production_date) ?? { ai: [], manual: [] };
    (r.ai_generated ? bucket.ai : bucket.manual).push(r.actual_cost_per_ton);
    byDate.set(r.production_date, bucket);
  }
  const dates = [...byDate.keys()].sort();
  const avg = (xs: number[]) =>
    xs.length ? Math.round((xs.reduce((s, x) => s + x, 0) / xs.length) * 10) / 10 : null;
  const costOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['AI 方案', '人工方案'] },
    grid: { left: 60, right: 30, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '元/吨' },
    series: [
      {
        name: 'AI 方案',
        type: 'line',
        connectNulls: true,
        data: dates.map((d) => avg(byDate.get(d)!.ai)),
      },
      {
        name: '人工方案',
        type: 'line',
        connectNulls: true,
        data: dates.map((d) => avg(byDate.get(d)!.manual)),
      },
    ],
  };

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        历史方案
        {mock && <MockBadge />}
      </h2>
      <Card
        size="small"
        className="mb-4"
        title="配煤方案记录"
        extra={
          <Select
            className="w-32"
            value={furnaceId}
            options={FURNACE_OPTIONS}
            onChange={setFurnaceId}
          />
        }
      >
        <Table<BlendRecipe>
          rowKey="batch_no"
          size="small"
          loading={loading}
          columns={columns}
          dataSource={recipes}
          pagination={{ pageSize: 10 }}
        />
      </Card>
      <Row gutter={16}>
        <Col span={24}>
          <ChartCard
            title="AI 方案 vs 人工方案实际成本对比"
            option={costOption}
            mock={mock}
          />
        </Col>
      </Row>
    </div>
  );
}
