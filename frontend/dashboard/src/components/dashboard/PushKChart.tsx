/**
 * 推焦 KPI 卡：K1/K2/K3 近 7 天三折线 + K3 目标 0.95 红色目标线（方案§4.2.6 考核口径）。
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import ChartCard from '../ChartCard';
import { darkLineOption } from './chartTheme';
import { aggregateByDate } from './kAggregate';
import { colors } from '../../styles/tokens';
import type { KCoefficientRow } from '../../api/types';

interface Props {
  rows: KCoefficientRow[];
  mock?: boolean;
}

/** K3 考核目标（方案§4.2.6 / 操作手册验收口径） */
const K3_TARGET = 0.95;

export default function PushKChart({ rows, mock = false }: Props) {
  const option = useMemo<EChartsOption>(() => {
    const daily = aggregateByDate(rows);
    const mk = (name: string, color: string, data: number[]) => ({
      name,
      type: 'line' as const,
      smooth: true,
      symbolSize: 6,
      lineStyle: { color },
      itemStyle: { color },
      data,
    });
    return darkLineOption(
      daily.map((d) => d.date),
      [
        mk('K3', colors.warning, daily.map((d) => d.k3)),
        mk('K1', colors.info, daily.map((d) => d.k1)),
        mk('K2', colors.success, daily.map((d) => d.k2)),
      ],
      { markLineValue: K3_TARGET, markLineName: 'K3目标 0.95' },
    );
  }, [rows]);

  return (
    <ChartCard title="推焦 KPI：K1 / K2 / K3 近 7 天" option={option} mock={mock} height={280} />
  );
}
