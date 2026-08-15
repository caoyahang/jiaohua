/**
 * 方案优化页：目标质量 + 煤种约束 → 三套方案对比（成本最优/质量最稳/综合推荐）→ 人工确认。
 * POST /blend/optimize 后端恒 503，必走 mock（README 接口清单）。
 */
import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  InputNumber,
  message,
  Row,
  Select,
  Table,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import { optimizeBlend } from '../api';
import { presetCoals } from '../api/mock';
import type {
  BlendSolution,
  CoalInfo,
  OptimizeResponse,
  SolutionType,
  TargetQuality,
} from '../api/types';
import ConfirmModal from '../components/ConfirmModal';
import MockBadge from '../components/MockBadge';

const SOLUTION_LABEL: Record<SolutionType, string> = {
  cost_optimal: '成本最优',
  quality_stable: '质量最稳',
  balanced: '综合推荐',
};

const PRIORITY_OPTIONS = [
  { value: 'cost', label: '成本优先' },
  { value: 'quality', label: '质量优先' },
  { value: 'balanced', label: '综合' },
] as const;

function pieOption(solution: BlendSolution): EChartsOption {
  return {
    tooltip: { trigger: 'item', valueFormatter: (v) => `${(Number(v) * 100).toFixed(1)}%` },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        label: { formatter: '{b}\n{d}%' },
        data: Object.entries(solution.blend_ratio)
          .filter(([, v]) => v > 0)
          .map(([name, value]) => ({ name, value })),
      },
    ],
  };
}

export default function OptimizePage() {
  const [target, setTarget] = useState<TargetQuality>({
    M25_min: 90,
    M10_max: 6.5,
    CSR_min: 65,
    CRI_max: 25,
  });
  const [maxCost, setMaxCost] = useState(1500);
  const [priority, setPriority] = useState<'cost' | 'quality' | 'balanced'>('balanced');
  const [coals, setCoals] = useState<CoalInfo[]>(presetCoals);
  const [result, setResult] = useState<(OptimizeResponse & { __mock?: true }) | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState<BlendSolution | null>(null);

  const patchCoal = (coalId: number, patch: Partial<CoalInfo>) => {
    setCoals((prev) =>
      prev.map((c) => (c.coal_id === coalId ? { ...c, ...patch } : c)),
    );
  };

  const onGenerate = async () => {
    setLoading(true);
    try {
      const resp = await optimizeBlend({
        target_quality: target,
        available_coals: coals,
        max_cost_per_ton: maxCost,
        priority,
      });
      setResult(resp);
      if (resp.__mock) message.info('后端优化器未就绪，展示演示方案');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '生成方案失败');
    } finally {
      setLoading(false);
    }
  };

  const onConfirmExecute = () => {
    // 本界面不做自动下发：AI 建议 + 人工确认，配煤师有最终决定权（方案§13.2）
    message.success(
      `已确认「${confirming ? SOLUTION_LABEL[confirming.type] : ''}」方案，请按操作规程人工下发执行`,
    );
    setConfirming(null);
  };

  const numCol = (
    title: string,
    key: 'stock_tons' | 'price_per_ton' | 'min_ratio' | 'max_ratio',
    toPercent = false,
  ): ColumnsType<CoalInfo>[number] => ({
    title,
    dataIndex: key,
    width: 110,
    render: (_, c) => (
      <InputNumber
        min={0}
        max={toPercent ? 100 : undefined}
        value={toPercent ? Math.round(c[key] * 100) : c[key]}
        onChange={(v) =>
          patchCoal(c.coal_id, { [key]: toPercent ? (v ?? 0) / 100 : (v ?? 0) })
        }
      />
    ),
  });

  const columns: ColumnsType<CoalInfo> = [
    { title: '煤种', dataIndex: 'name', width: 90, fixed: 'left' },
    numCol('库存 (吨)', 'stock_tons'),
    numCol('单价 (元/吨)', 'price_per_ton'),
    numCol('配比下限 (%)', 'min_ratio', true),
    numCol('配比上限 (%)', 'max_ratio', true),
    {
      title: '化验指标',
      key: 'lab',
      render: (_, c) =>
        `Ad ${String(c.lab_data.Ad)}% / Vdaf ${String(c.lab_data.Vdaf)}% / St,d ${String(c.lab_data.St_d)}% / G ${String(c.lab_data.G)} / Y ${String(c.lab_data.Y)}mm / Rmax ${String(c.lab_data.Rmax)}`,
    },
  ];

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        方案优化
        {result?.__mock && <MockBadge />}
      </h2>
      <Card size="small" title="目标与约束" className="mb-4">
        <Form layout="inline">
          <Form.Item label="M25 ≥ (%)">
            <InputNumber
              value={target.M25_min}
              onChange={(v) => setTarget({ ...target, M25_min: v ?? 0 })}
            />
          </Form.Item>
          <Form.Item label="M10 ≤ (%)">
            <InputNumber
              value={target.M10_max}
              onChange={(v) => setTarget({ ...target, M10_max: v ?? 0 })}
            />
          </Form.Item>
          <Form.Item label="CSR ≥ (%)">
            <InputNumber
              value={target.CSR_min}
              onChange={(v) => setTarget({ ...target, CSR_min: v ?? 0 })}
            />
          </Form.Item>
          <Form.Item label="CRI ≤ (%)">
            <InputNumber
              value={target.CRI_max}
              onChange={(v) => setTarget({ ...target, CRI_max: v ?? 0 })}
            />
          </Form.Item>
          <Form.Item label="成本上限 (元/吨)">
            <InputNumber
              min={1}
              value={maxCost}
              onChange={(v) => setMaxCost(v ?? 1500)}
            />
          </Form.Item>
          <Form.Item label="偏好">
            <Select
              className="w-28"
              value={priority}
              options={[...PRIORITY_OPTIONS]}
              onChange={setPriority}
            />
          </Form.Item>
        </Form>
      </Card>
      <Card size="small" title="可用煤种" className="mb-4">
        <Table<CoalInfo>
          rowKey="coal_id"
          size="small"
          pagination={false}
          scroll={{ x: 900 }}
          columns={columns}
          dataSource={coals}
        />
        <Button
          type="primary"
          className="mt-3"
          loading={loading}
          onClick={onGenerate}
        >
          生成方案
        </Button>
      </Card>
      {result && (
        <>
          <Row gutter={16}>
            {result.solutions.map((s) => (
              <Col span={8} key={s.type}>
                <Card size="small" title={SOLUTION_LABEL[s.type]}>
                  <ReactECharts
                    option={pieOption(s)}
                    // 图表容器需显式高度（非颜色/排版样式）
                    style={{ height: 200 }}
                    notMerge
                  />
                  <p>预估成本：{s.estimated_cost} 元/吨</p>
                  <p>
                    预测质量：M25 {s.predicted_quality.M25}% / M10{' '}
                    {s.predicted_quality.M10}% / CSR {s.predicted_quality.CSR}%
                    / CRI {s.predicted_quality.CRI}%
                  </p>
                  <p>置信度：{(s.confidence * 100).toFixed(0)}%</p>
                  <Alert type="info" message={s.explanation} className="mb-3" />
                  <Button
                    type="primary"
                    block
                    onClick={() => setConfirming(s)}
                  >
                    确认执行
                  </Button>
                </Card>
              </Col>
            ))}
          </Row>
          <p className="mt-2 text-textSecondary">
            模型版本：{result.model_version}；耗时 {result.compute_time_ms} ms
          </p>
        </>
      )}
      <ConfirmModal
        open={confirming !== null}
        title="确认执行方案"
        okText="确认执行"
        content={
          <div>
            <p>
              即将确认「{confirming ? SOLUTION_LABEL[confirming.type] : ''}」方案。
            </p>
            <p>
              AI 方案仅供参考，配煤师始终有最终决定权（方案§13.2）。
              确认后请按操作规程人工下发，本界面不做自动下发。
            </p>
          </div>
        }
        onConfirm={onConfirmExecute}
        onCancel={() => setConfirming(null)}
      />
    </div>
  );
}
