/**
 * 质量趋势：M25/M10/CSR/CRI 指标切换 + 实测与 AI 预测对比。
 * 数据源：固定 mock（后端无 coke_quality 查询接口），角标常显，字段对齐 coke_quality 表。
 */
import { useMemo, useState } from 'react';
import type { EChartsOption } from 'echarts';
import { Segmented } from 'antd';
import ChartCard from '../ChartCard';
import { chartPalette, lineOption } from './chartTheme';
import type { QualityBatch } from '../../api/types';

interface Props {
  batches: QualityBatch[];
  mock?: boolean;
}

/** 指标键与中文名（字段对齐 coke_quality 表 m25/pred_m25 等） */
const METRICS = [
  { key: 'm25', label: 'M25 抗碎强度' },
  { key: 'm10', label: 'M10 耐磨强度' },
  { key: 'csr', label: 'CSR 反应后强度' },
  { key: 'cri', label: 'CRI 反应性' },
] as const;

type MetricKey = (typeof METRICS)[number]['key'];

export default function QualityPanel({ batches, mock = true }: Props) {
  const [metric, setMetric] = useState<MetricKey>('m25');

  const option = useMemo<EChartsOption>(() => {
    const predKey = `pred_${metric}` as keyof QualityBatch;
    return lineOption(
      batches.map((b) => b.batch_no.slice(2, 10)),
      [
        {
          name: '实测值',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          lineStyle: { color: chartPalette.main },
          itemStyle: { color: chartPalette.main },
          data: batches.map((b) => b[metric] as number),
        },
        {
          name: 'AI 预测值',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          lineStyle: { color: chartPalette.compare, type: 'dashed' },
          itemStyle: { color: chartPalette.compare },
          data: batches.map((b) => b[predKey] as number),
        },
      ],
      { autoY: true },
    );
  }, [batches, metric]);

  return (
    <ChartCard
      title="焦炭质量趋势：实测与 AI 预测"
      option={option}
      mock={mock}
      height={300}
    >
      <Segmented<MetricKey>
        size="small"
        value={metric}
        onChange={setMetric}
        options={METRICS.map((m) => ({ label: m.label, value: m.key }))}
      />
    </ChartCard>
  );
}
