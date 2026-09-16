/**
 * ECharts 卡片容器：统一运营总览图表的面板、标题、角标与高度。
 * 依据方案§7.2 阶段六。
 */
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { ReactNode } from 'react';
import Panel from './dashboard/Panel';

interface ChartCardProps {
  title: string;
  option: EChartsOption;
  /** 图表高度（px），默认 280 */
  height?: number;
  /** 透传给 Panel 根节点 */
  className?: string;
  /** 数据源为 mock 时传 true，显示「演示数据」角标 */
  mock?: boolean;
  extra?: ReactNode;
  /** 图表上方的工具区（如指标切换器），放正文区避免标题栏拥挤 */
  children?: ReactNode;
}

export default function ChartCard({
  title,
  option,
  height = 280,
  className,
  mock = false,
  extra,
  children,
}: ChartCardProps) {
  return (
    <Panel title={title} mock={mock} extra={extra} className={className}>
      {children && <div className="mb-2">{children}</div>}
      <ReactECharts
        option={option}
        className="w-full"
        // 高度属图表容器固有属性，非颜色/排版样式。
        style={{ height }}
        notMerge
      />
    </Panel>
  );
}
