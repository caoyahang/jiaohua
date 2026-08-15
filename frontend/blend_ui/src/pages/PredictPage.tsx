/**
 * 质量预测页：输入煤种配比 → 显示预测 M25/M10/CSR/CRI + 各煤种影响解释。
 * 后端暂无独立预测接口，固定走演示实现（README 接口清单，方案§4.1.6 冷启动经验模型）。
 */
import { useMemo, useState } from 'react';
import { Alert, Button, Card, Col, InputNumber, Row, Statistic, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { EChartsOption } from 'echarts';
import { predictQuality } from '../api';
import { presetCoals } from '../api/mock';
import type { PredictResponse } from '../api/types';
import ChartCard from '../components/ChartCard';
import MockBadge from '../components/MockBadge';

interface RatioRow {
  name: string;
  labSummary: string;
  ratio: number; // 百分比 0~100
}

const initialRows: RatioRow[] = presetCoals.map((c) => ({
  name: c.name,
  labSummary: `Ad ${String(c.lab_data.Ad)}% / Vdaf ${String(c.lab_data.Vdaf)}% / G ${String(c.lab_data.G)}`,
  ratio: Math.round(100 / presetCoals.length),
}));

export default function PredictPage() {
  const [rows, setRows] = useState<RatioRow[]>(initialRows);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const total = useMemo(
    () => rows.reduce((s, r) => s + (r.ratio || 0), 0),
    [rows],
  );
  const totalOk = Math.abs(total - 100) < 1e-6;

  const setRatio = (name: string, value: number | null) => {
    setRows((prev) =>
      prev.map((r) => (r.name === name ? { ...r, ratio: value ?? 0 } : r)),
    );
  };

  const onPredict = async () => {
    setLoading(true);
    try {
      const ratios = Object.fromEntries(
        rows.map((r) => [r.name, r.ratio / 100]),
      );
      setResult(await predictQuality({ ratios }));
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<RatioRow> = [
    { title: '煤种', dataIndex: 'name', width: 100 },
    { title: '化验指标', dataIndex: 'labSummary' },
    {
      title: '配比 (%)',
      dataIndex: 'ratio',
      width: 140,
      render: (_, row) => (
        <InputNumber
          min={0}
          max={100}
          step={1}
          value={row.ratio}
          onChange={(v) => setRatio(row.name, v)}
        />
      ),
    },
  ];

  const impactOption: EChartsOption = {
    grid: { left: 80, right: 30, top: 10, bottom: 30 },
    xAxis: { type: 'value', name: '影响值' },
    yAxis: {
      type: 'category',
      data: (result?.explanations ?? []).map((e) => e.coal),
    },
    series: [
      {
        type: 'bar',
        data: (result?.explanations ?? []).map((e) => e.impact),
        label: { show: true, position: 'right' },
      },
    ],
  };

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        质量预测
        {result && <MockBadge />}
      </h2>
      <Row gutter={16}>
        <Col span={10}>
          <Card size="small" title="煤种配比输入">
            <Table<RatioRow>
              rowKey="name"
              size="small"
              pagination={false}
              columns={columns}
              dataSource={rows}
            />
            <div className="mt-3 flex items-center justify-between">
              <span className={totalOk ? '' : 'text-danger font-bold'}>
                合计：{total.toFixed(0)}%{!totalOk && '（必须等于 100%）'}
              </span>
              <Button
                type="primary"
                disabled={!totalOk}
                loading={loading}
                onClick={onPredict}
              >
                预测质量
              </Button>
            </div>
          </Card>
        </Col>
        <Col span={14}>
          <Card size="small" title="预测焦炭质量" className="mb-4">
            {result ? (
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic title="抗碎强度 M25 (%)" value={result.predicted_quality.M25} />
                </Col>
                <Col span={6}>
                  <Statistic title="耐磨强度 M10 (%)" value={result.predicted_quality.M10} />
                </Col>
                <Col span={6}>
                  <Statistic title="反应后强度 CSR (%)" value={result.predicted_quality.CSR} />
                </Col>
                <Col span={6}>
                  <Statistic title="反应性 CRI (%)" value={result.predicted_quality.CRI} />
                </Col>
              </Row>
            ) : (
              <span className="text-textSecondary">
                输入配比后点击「预测质量」
              </span>
            )}
          </Card>
          {result && (
            <ChartCard
              title="各煤种影响解释"
              option={impactOption}
              height={220}
              mock
            />
          )}
        </Col>
      </Row>
      <Alert
        className="mt-4"
        type="info"
        showIcon
        message="当前为冷启动经验模型（方案§4.1.6），系数待 DOE 试验标定，预测结果仅供参考。"
      />
    </div>
  );
}
