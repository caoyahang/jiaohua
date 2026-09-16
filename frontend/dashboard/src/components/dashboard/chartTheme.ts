/**
 * 运营总览 ECharts 公共主题：坐标轴、提示框和系列颜色统一取 tokens。
 * 依据前端规范§3 红线4，组件内不出现颜色字面量。
 */
import type { EChartsOption, SeriesOption } from 'echarts';
import { colors } from '../../styles/tokens';

export const chartPalette = {
  main: colors.primary,
  compare: colors.warning,
  ok: colors.success,
} as const;

/** 折线图公共浅色骨架：类目轴、数值轴与 tooltip。 */
export function lineOption(
  categories: string[],
  series: SeriesOption[],
  extra?: { markLineValue?: number; markLineName?: string; autoY?: boolean },
): EChartsOption {
  const markLine = extra?.markLineValue !== undefined
    ? {
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: colors.danger, type: 'dashed' as const },
          label: { color: colors.danger, formatter: extra.markLineName ?? '目标' },
          data: [{ yAxis: extra.markLineValue }],
        },
      }
    : {};

  return {
    backgroundColor: 'transparent',
    grid: { left: 44, right: 16, top: 36, bottom: 28 },
    legend: { textStyle: { color: colors.textSecondary } },
    tooltip: {
      trigger: 'axis',
      backgroundColor: colors.bgCard,
      borderColor: colors.border,
      textStyle: { color: colors.text },
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: colors.border } },
      axisLabel: { color: colors.textSecondary },
    },
    yAxis: {
      type: 'value',
      ...(extra?.autoY
        ? { scale: true }
        : {
            min: (value: { min: number }) =>
              Math.floor(Math.min(value.min, extra?.markLineValue ?? 1) * 100 - 2) / 100,
            max: 1.05,
          }),
      splitLine: { lineStyle: { color: colors.border } },
      axisLabel: { color: colors.textSecondary },
    },
    series: series.map((item, index) => (index === 0 ? { ...item, ...markLine } : item)),
  };
}

/** 饼图公共浅色骨架。 */
export function pieOption(data: { name: string; value: number }[]): EChartsOption {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: colors.bgCard,
      borderColor: colors.border,
      textStyle: { color: colors.text },
    },
    legend: { bottom: 0, textStyle: { color: colors.textSecondary } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '43%'],
        label: { color: colors.text },
        data,
      },
    ],
  };
}
