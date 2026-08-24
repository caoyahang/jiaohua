/**
 * ECharts 深色大屏主题：坐标轴/文字/tooltip/网格颜色统一取 tokens（红线4）。
 * 所有图表卡片的公共 option 片段从这里出，组件内不出现颜色字面量。
 */
import type { EChartsOption, SeriesOption } from 'echarts';
import { colors, darkColors } from '../../styles/tokens';

/**
 * 大屏图表系列色板（同源引用 tokens，组件内不出现颜色字面量）。
 * main=主系列（青），compare=对比/预测系列（橙），ok=辅助/达标系列（绿）。
 */
export const chartPalette = {
  main: darkColors.accentCyan,
  compare: darkColors.accentOrange,
  ok: colors.success,
} as const;

/** 折线图的公共深色骨架：类目轴 + 数值轴 + tooltip */
export function darkLineOption(
  categories: string[],
  series: SeriesOption[],
  extra?: { markLineValue?: number; markLineName?: string; autoY?: boolean },
): EChartsOption {
  const markLine =
    extra?.markLineValue !== undefined
      ? {
          // 目标线为工艺考核红线口径（如 K均≥0.90 / K3≥0.95）
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: darkColors.alarmRed, type: 'dashed' as const },
            label: {
              color: darkColors.alarmRed,
              formatter: extra.markLineName ?? '目标',
            },
            data: [{ yAxis: extra.markLineValue }],
          },
        }
      : {};
  return {
    backgroundColor: 'transparent',
    grid: { left: 44, right: 16, top: 36, bottom: 28 },
    legend: { textStyle: { color: darkColors.textSecondary } },
    tooltip: {
      trigger: 'axis',
      backgroundColor: darkColors.bgCard,
      borderColor: darkColors.accentCyanDim,
      textStyle: { color: darkColors.text },
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: darkColors.border } },
      axisLabel: { color: darkColors.textSecondary },
    },
    yAxis: {
      type: 'value',
      // autoY（质量看板等数值域非 0~1 的图）：交给 ECharts 自适应；
      // 否则按 K 系数域固定 max=1.05，min 下探以让目标线入视野
      ...(extra?.autoY
        ? { scale: true }
        : {
            // 整数标度再回除：避免 0.94-0.02=0.91999… 浮点串直接画到刻度标签上
            min: (v: { min: number }) =>
              Math.floor(Math.min(v.min, extra?.markLineValue ?? 1) * 100 - 2) / 100,
            max: 1.05,
          }),
      splitLine: { lineStyle: { color: darkColors.gridLine } },
      axisLabel: { color: darkColors.textSecondary },
    },
    // 目标线挂在第一条系列上
    series: series.map((s, i) => (i === 0 ? { ...s, ...markLine } : s)),
  };
}

/** 饼图的公共深色骨架 */
export function darkPieOption(
  data: { name: string; value: number }[],
): EChartsOption {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: darkColors.bgCard,
      borderColor: darkColors.border,
      textStyle: { color: darkColors.text },
    },
    legend: {
      bottom: 0,
      textStyle: { color: darkColors.textSecondary },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '44%'],
        label: { color: darkColors.text },
        data,
      },
    ],
  };
}
