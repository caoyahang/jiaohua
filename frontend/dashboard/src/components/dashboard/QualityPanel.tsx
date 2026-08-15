/**
 * 质量看板：M25/M10/CSR/CRI 指标切换（Segmented）+ 实测 vs AI 预测双线（近 10 批次）。
 * 数据源：固定 mock（后端无 coke_quality 查询接口），角标常显，字段对齐 coke_quality 表。
 */
import { useMemo, useState } from 'react';
import type { EChartsOption } from 'echarts';
import { Segmented } from 'antd';
import ChartCard from '../ChartCard';
import { darkLineOption } from './chartTheme';
import { colors } from '../../styles/tokens';
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
    return darkLineOption(
      batches.map((b) => b.batch_no.slice(2, 10)),
      [
        {
          name: '实测值',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          lineStyle: { color: colors.info },
          itemStyle: { color: colors.info },
          data: batches.map((b) => b[metric] as number),
        },
        {
          name: 'AI 预测值',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          lineStyle: { color: colors.warning, type: 'dashed' },
          itemStyle: { color: colors.warning },
          data: batches.map((b) => b[predKey] as number),
        },
      ],
      { autoY: true },
    );
  }, [batches, metric]);

  return (
    <ChartCard
      title="质量看板：实测 vs AI 预测（近 10 批次）"
      option={option}
      mock={mock}
      height={280}
      extra={
        <Segmented<MetricKey>
          size="small"
          value={metric}
          onChange={setMetric}
          options={METRICS.map((m) => ({ label: m.label, value: m.key }))}
        />
      }
    />
  );
}
