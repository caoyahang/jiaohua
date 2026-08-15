/**
 * 顶部 KPI 卡片区（5 张）：成本节约 / 预测准确率 / 煤气消耗 / 非计划停机 / 未确认安全告警数。
 * 汇总 KPI 后端无聚合接口 → 固定 mock，角标常显；未确认告警数由 vision+pdm 告警计算。
 */
import { Card } from 'antd';
import MockBadge from '../MockBadge';
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
  value: string;
  unit: string;
  mock: boolean;
  /** 告警卡：>0 时红框红字 */
  alert?: boolean;
}

export default function KpiCards({ overview, unackedAlarms, overviewMock, alarmsMock }: Props) {
  const items: KpiItem[] = [
    {
      label: '本月配煤成本节约',
      value: overview ? overview.cost_saving_wan.toFixed(1) : '--',
      unit: '万元',
      mock: overviewMock,
    },
    {
      label: '质量预测准确率',
      value: overview ? overview.quality_accuracy_pct.toFixed(1) : '--',
      unit: '%',
      mock: overviewMock,
    },
    {
      label: '煤气消耗',
      value: overview ? String(overview.gas_consumption_m3h) : '--',
      unit: 'm³/h',
      mock: overviewMock,
    },
    {
      label: '本月非计划停机',
      value: overview ? String(overview.unplanned_stops) : '--',
      unit: '次',
      mock: overviewMock,
    },
    {
      label: '未确认安全告警',
      value: String(unackedAlarms),
      unit: '条',
      mock: alarmsMock,
      alert: unackedAlarms > 0,
    },
  ];

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-3">
      {items.map((it) => (
        <Card
          key={it.label}
          size="small"
          className={it.alert ? 'border-darkAlarmRed' : undefined}
        >
          <div className="text-darkTextSecondary text-xs">
            {it.label}
            {it.mock && <MockBadge />}
          </div>
          <div
            className={`mt-1 text-2xl font-bold font-mono ${
              it.alert ? 'text-darkAlarmRed' : 'text-darkKpiValue'
            }`}
          >
            {it.value}
            <span className="ml-1 text-xs font-normal text-darkTextSecondary">{it.unit}</span>
          </div>
        </Card>
      ))}
    </div>
  );
}
