/**
 * 单机详情页图表 option 构造（与样式分离，页面文件只组装）。
 * 颜色一律取自 tokens（红线4）。
 * 红线：不展示 RUL 剩余寿命（方案§4.3，故障样本不足，该能力后置）。
 */
import type { EChartsOption } from 'echarts';
import { colors } from '../styles/tokens';

/** 近 7 天日期标签（MM-DD，旧→新） */
export function last7DayLabels(): string[] {
  const labels: string[] = [];
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date(Date.now() - i * 86400_000);
    labels.push(d.toISOString().slice(5, 10));
  }
  return labels;
}

/** 健康评分仪表盘（0~100 色带：差红 / 中黄 / 好绿） */
export function gaugeOption(score: number): EChartsOption {
  return {
    series: [
      {
        type: 'gauge',
        min: 0,
        max: 100,
        startAngle: 210,
        endAngle: -30,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.6, colors.danger],
              [0.8, colors.warning],
              [1, colors.success],
            ],
          },
        },
        pointer: { length: '60%' },
        axisTick: { distance: -18, length: 6 },
        splitLine: { distance: -18, length: 18 },
        axisLabel: { distance: -40, fontSize: 10 },
        detail: {
          valueAnimation: true,
          formatter: '{value} 分',
          fontSize: 20,
          offsetCenter: [0, '70%'],
        },
        data: [{ value: score }],
      },
    ],
  };
}

/** 7 天健康趋势折线 */
export function healthTrendOption(trend: number[]): EChartsOption {
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: last7DayLabels() },
    yAxis: { type: 'value', name: '健康评分', min: 0, max: 100 },
    series: [
      {
        name: '健康评分',
        type: 'line',
        smooth: true,
        data: trend,
        lineStyle: { color: colors.primary },
        itemStyle: { color: colors.primary },
        areaStyle: { color: colors.primary, opacity: 0.12 },
      },
    ],
  };
}

/** ISO 10816 四区边界（mm/s） */
const ISO_BOUNDS = [2.3, 4.5, 7.1] as const;
const ZONE_META = [
  { name: '良好', color: colors.success },
  { name: '注意', color: colors.warning },
  { name: '不合格', color: colors.orange },
  { name: '危险', color: colors.danger },
] as const;

/** 振动速度趋势 + ISO 10816 四区背景色带（markArea） */
export function vibrationTrendOption(trend: number[]): EChartsOption {
  const yMax = Math.max(9, Math.ceil(Math.max(...trend) + 1));
  const bands: [number, number][] = [
    [0, ISO_BOUNDS[0]],
    [ISO_BOUNDS[0], ISO_BOUNDS[1]],
    [ISO_BOUNDS[1], ISO_BOUNDS[2]],
    [ISO_BOUNDS[2], yMax],
  ];
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: last7DayLabels() },
    yAxis: { type: 'value', name: 'mm/s', min: 0, max: yMax },
    series: [
      {
        name: '振动速度',
        type: 'line',
        smooth: true,
        data: trend,
        lineStyle: { color: colors.info },
        itemStyle: { color: colors.info },
        markArea: {
          silent: true,
          data: bands.map(([y0, y1], i) => [
            {
              yAxis: y0,
              itemStyle: { color: ZONE_META[i].color, opacity: 0.12 },
              label: { show: true, position: 'insideRight', color: ZONE_META[i].color },
              name: ZONE_META[i].name,
            },
            { yAxis: y1 },
          ]),
        },
      },
    ],
  };
}
