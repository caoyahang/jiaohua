/**
 * KPI 卡片区（5 张）：成本节约 / 预测准确率 / 煤气消耗 / 非计划停机 / 未确认安全告警数。
 * 汇总 KPI 后端无聚合接口 → 固定 mock，角标常显；未确认告警数由 vision+pdm 告警计算。
 * 数值用 DataV DigitalFlop 翻牌器（{nt} 千分位，10s 轮询时滚动动画）；
 * 样式：半透明深色小卡 + 左侧色条（告警卡转橙色），颜色全走 dark* token。
 */
import { DigitalFlop } from '@jiaminghi/data-view-react';
import MockBadge from '../MockBadge';
import { darkColors } from '../../styles/tokens';
import type { OverviewKpi } from '../../api/types';

interface Props {
  overview: OverviewKpi | null;
  /** 未确认安全告警数（视觉 + PdM） */
  unackedAlarms: number;
  /** 汇总 KPI 恒为 mock（后端无接口），告警数随告警区块的数据源 */
  overviewMock: boolean;
  alarmsMock: boolean;
}

interface KpiItem {
  label: string;
  /** null = 数据未就绪，显示占位符 */
  value: number | null;
  unit: string;
  /** DigitalFlop 小数位 */
  toFixed: number;
  mock: boolean;
  /** 告警卡：>0 时橙色描边橙字 */
  alert?: boolean;
}

export default function KpiCards({ overview, unackedAlarms, overviewMock, alarmsMock }: Props) {
  const items: KpiItem[] = [
    {
      label: '本月配煤成本节约',
      value: overview?.cost_saving_wan ?? null,
      unit: '万元',
      toFixed: 1,
      mock: overviewMock,
    },
    {
      label: '质量预测准确率',
      value: overview?.quality_accuracy_pct ?? null,
      unit: '%',
      toFixed: 1,
      mock: overviewMock,
    },
    {
      label: '煤气消耗',
      value: overview?.gas_consumption_m3h ?? null,
      unit: 'm³/h',
      toFixed: 0,
      mock: overviewMock,
    },
    {
      label: '本月非计划停机',
      value: overview?.unplanned_stops ?? null,
      unit: '次',
      toFixed: 0,
      mock: overviewMock,
    },
    {
      label: '未确认安全告警',
      value: unackedAlarms,
      unit: '条',
      toFixed: 0,
      mock: alarmsMock,
      alert: unackedAlarms > 0,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {items.map((it) => (
        <div
          key={it.label}
          className={`relative border bg-darkCard/70 px-3 py-2 ${
            it.alert ? 'border-darkAccentOrange' : 'border-darkAccentCyanDim/60'
          }`}
        >
          {/* 左侧色条：告警卡橙色，其余青色 */}
          <span
            className={`absolute bottom-0 left-0 top-0 w-0.5 ${
              it.alert ? 'bg-darkAccentOrange' : 'bg-darkAccentCyan'
            }`}
          />
          <div className="text-xs text-darkTextSecondary">
            {it.label}
            {it.mock && <MockBadge />}
          </div>
          <div className="mt-1 flex items-end">
            {it.value === null ? (
              <span className="font-mono text-xl font-bold text-darkAccentCyan">--</span>
            ) : (
              <div className="min-w-0 flex-1">
                <DigitalFlop
                  config={{
                    number: [it.value],
                    content: '{nt}',
                    toFixed: it.toFixed,
                    textAlign: 'left',
                    // 千分位：{nt} 仅为占位符，分隔符靠 formatter 补（toLocaleString 美式逗号）
                    formatter: (n) => Number(n).toLocaleString('en-US'),
                    style: {
                      fontSize: 22,
                      // 翻牌器文字色走 token（DataV 组件接口）
                      fill: it.alert ? darkColors.accentOrange : darkColors.kpiValue,
                      fontWeight: 700,
                    },
                  }}
                  // DataV 组件接口：翻牌器画布尺寸靠 style 传入（非业务内联样式）
                  style={{ width: '100%', height: '30px' }}
                />
              </div>
            )}
            <span className="ml-1 shrink-0 text-xs text-darkTextSecondary">{it.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
