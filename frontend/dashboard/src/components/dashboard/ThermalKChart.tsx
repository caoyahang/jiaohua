/**
 * 热工 KPI 卡：K均/K安 近 7 天双折线 + K均目标 0.90 红色目标线（方案§4.2.6 考核口径）。
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import ChartCard from '../ChartCard';
import { chartPalette, lineOption } from './chartTheme';
import { aggregateByDate } from './kAggregate';
import type { KCoefficientRow } from '../../api/types';

interface Props {
  rows: KCoefficientRow[];
  mock?: boolean;
}

/** K均考核目标（方案§4.2.6 / 操作手册验收口径） */
const K_UNIFORM_TARGET = 0.9;

export default function ThermalKChart({ rows, mock = false }: Props) {
  const option = useMemo<EChartsOption>(() => {
    const daily = aggregateByDate(rows);
    return lineOption(
      daily.map((d) => d.date),
      [
        {
          name: 'K均',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          lineStyle: { color: chartPalette.main },
          itemStyle: { color: chartPalette.main },
          data: daily.map((d) => d.k_uniform),
        },
        {
          name: 'K安',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          lineStyle: { color: chartPalette.ok },
          itemStyle: { color: chartPalette.ok },
          data: daily.map((d) => d.k_stable),
        },
      ],
      { markLineValue: K_UNIFORM_TARGET, markLineName: 'K均目标 0.90' },
    );
  }, [rows]);

  return (
    <ChartCard title="热工稳定性趋势（K均 / K安）" option={option} mock={mock} />
  );
}
