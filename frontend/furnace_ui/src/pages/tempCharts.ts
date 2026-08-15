/**
 * 炉温监控页的 ECharts option 构建器（逻辑与组装分离，单文件行数红线）。
 * 颜色全部来自 tokens（红线4），换向期用灰色 markArea 标注（方案§4.2.6）。
 */
import type { EChartsOption } from 'echarts';
import type { TempPoint } from '../api/types';
import { colors } from '../styles/tokens';

/** ISO 时间戳 → HH:mm */
function fmtTime(ts: string): string {
  const d = new Date(ts);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

/** 取某一侧的时序（mock 按时间升序、机/焦交替排列，filter 后仍升序） */
function sidePoints(points: TempPoint[], side: 'machine' | 'coke'): TempPoint[] {
  return points.filter((p) => p.burner_side === side);
}

/** 换向期 markArea：把连续的 switching 点合并为区间段（起止二元组） */
function switchingAreas(
  times: string[],
  points: TempPoint[],
): [{ xAxis: string }, { xAxis: string }][] {
  const areas: [{ xAxis: string }, { xAxis: string }][] = [];
  let start = -1;
  for (let i = 0; i < points.length; i += 1) {
    if (points[i].switching && start < 0) start = i;
    if (start >= 0 && (!points[i].switching || i === points.length - 1)) {
      const end = points[i].switching ? i : i - 1;
      areas.push([{ xAxis: times[start] }, { xAxis: times[end] }]);
      start = -1;
    }
  }
  return areas;
}

/** 机/焦侧火道温度双折线 + 换向期灰色 markArea */
export function buildTempOption(points: TempPoint[]): EChartsOption {
  const machine = sidePoints(points, 'machine');
  const coke = sidePoints(points, 'coke');
  const times = machine.map((p) => fmtTime(p.ts));
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['机侧火道温度', '焦侧火道温度'] },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: {
      type: 'value',
      name: '℃',
      min: 1150,
      max: 1280,
    },
    series: [
      {
        name: '机侧火道温度',
        type: 'line',
        showSymbol: false,
        color: colors.primary,
        data: machine.map((p) => p.fire_channel_temp),
        markArea: {
          silent: true,
          itemStyle: { color: colors.border },
          label: { show: true, formatter: '换向期', color: colors.textSecondary },
          data: switchingAreas(times, machine),
        },
      },
      {
        name: '焦侧火道温度',
        type: 'line',
        showSymbol: false,
        color: colors.danger,
        data: coke.map((p) => p.fire_channel_temp),
      },
    ],
  };
}

/** 煤气流量 / 烟道吸力 / 集气管压力 / 残氧多曲线图（双侧取均值） */
export function buildGasOption(points: TempPoint[]): EChartsOption {
  const machine = sidePoints(points, 'machine');
  const coke = sidePoints(points, 'coke');
  const times = machine.map((p) => fmtTime(p.ts));
  // 同一时刻双侧取均值作为全炉口径
  const avg = (key: 'gas_flow' | 'flue_suction' | 'collector_pressure' | 'oxygen_content') =>
    machine.map((p, i) => Math.round(((p[key] + coke[i][key]) / 2) * 100) / 100);
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['煤气流量', '烟道吸力', '集气管压力', '废气残氧'] },
    grid: { left: 70, right: 60, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '流量 m³/h' },
      { type: 'value', name: 'Pa / %' },
    ],
    series: [
      {
        name: '煤气流量',
        type: 'line',
        showSymbol: false,
        color: colors.primary,
        data: avg('gas_flow'),
      },
      {
        name: '烟道吸力',
        type: 'line',
        showSymbol: false,
        yAxisIndex: 1,
        color: colors.warning,
        data: avg('flue_suction'),
      },
      {
        name: '集气管压力',
        type: 'line',
        showSymbol: false,
        yAxisIndex: 1,
        color: colors.success,
        data: avg('collector_pressure'),
      },
      {
        name: '废气残氧',
        type: 'line',
        showSymbol: false,
        yAxisIndex: 1,
        color: colors.info,
        data: avg('oxygen_content'),
      },
    ],
  };
}
