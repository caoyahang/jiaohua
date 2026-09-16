/**
 * 运营总览核心指标卡：成本、质量、能耗、停机和未确认告警。
 * 指标口径依据方案§10.1；后端未提供的聚合数据明确标记为演示数据。
 */
import type { ReactNode } from 'react';
import {
  AlertOutlined,
  DollarOutlined,
  ExperimentOutlined,
  FireOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import MockBadge from '../MockBadge';
import type { OverviewKpi } from '../../api/types';

interface Props {
  overview: OverviewKpi | null;
  unackedAlarms: number;
  overviewMock: boolean;
  alarmsMock: boolean;
}

interface KpiItem {
  label: string;
  value: number | null;
  unit: string;
  digits: number;
  helper: string;
  icon: ReactNode;
  mock: boolean;
  alert?: boolean;
}

export default function KpiCards({ overview, unackedAlarms, overviewMock, alarmsMock }: Props) {
  const items: KpiItem[] = [
    {
      label: '本月配煤成本节约', value: overview?.cost_saving_wan ?? null, unit: '万元', digits: 1,
      helper: '对比同口径基线', icon: <DollarOutlined />, mock: overviewMock,
    },
    {
      label: '质量预测准确率', value: overview?.quality_accuracy_pct ?? null, unit: '%', digits: 1,
      helper: '焦炭质量预测', icon: <ExperimentOutlined />, mock: overviewMock,
    },
    {
      label: '煤气消耗', value: overview?.gas_consumption_m3h ?? null, unit: 'm³/h', digits: 0,
      helper: '当前小时均值', icon: <FireOutlined />, mock: overviewMock,
    },
    {
      label: '本月非计划停机', value: overview?.unplanned_stops ?? null, unit: '次', digits: 0,
      helper: '设备运行统计', icon: <ToolOutlined />, mock: overviewMock,
    },
    {
      label: '未确认安全告警', value: unackedAlarms, unit: '条', digits: 0,
      helper: unackedAlarms > 0 ? '需要及时处理' : '当前无待处理项', icon: <AlertOutlined />,
      mock: alarmsMock, alert: unackedAlarms > 0,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {items.map((item) => (
        <section key={item.label} className="rounded-lg border border-border bg-bgCard p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 text-sm text-textSecondary">
              <span>{item.label}</span>
              {item.mock && <MockBadge />}
            </div>
            <span className={`text-lg ${item.alert ? 'text-danger' : 'text-primary'}`}>{item.icon}</span>
          </div>
          <div className={`mt-3 text-2xl font-semibold ${item.alert ? 'text-danger' : 'text-text'}`}>
            {item.value === null ? '--' : item.value.toLocaleString('zh-CN', {
              minimumFractionDigits: item.digits,
              maximumFractionDigits: item.digits,
            })}
            <span className="ml-1 text-xs font-normal text-textSecondary">{item.unit}</span>
          </div>
          <div className="mt-2 text-xs text-textSecondary">{item.helper}</div>
        </section>
      ))}
    </div>
  );
}
