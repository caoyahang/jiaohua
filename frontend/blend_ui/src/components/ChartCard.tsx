/**
 * ECharts 卡片容器：统一图表卡片的标题、角标与高度。
 */
import { Card } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { ReactNode } from 'react';
import MockBadge from './MockBadge';

interface ChartCardProps {
  title: string;
  option: EChartsOption;
  /** 图表高度（px），默认 300 */
  height?: number;
  /** 数据源为 mock 时传 true，显示「演示数据」角标 */
  mock?: boolean;
  extra?: ReactNode;
}

export default function ChartCard({
  title,
  option,
  height = 300,
  mock = false,
  extra,
}: ChartCardProps) {
  return (
    <Card
      size="small"
      title={
        <span>
          {title}
          {mock && <MockBadge />}
        </span>
      }
      extra={extra}
    >
      <ReactECharts
        option={option}
        className="w-full"
        // 高度属图表容器固有属性，非颜色/排版样式
        style={{ height }}
        notMerge
      />
    </Card>
  );
}
