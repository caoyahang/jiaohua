/**
 * ECharts 卡片容器：统一图表卡片的面板外壳（Panel）、标题、角标与高度。
 * fillHeight 模式用 ResizeObserver 驱动 chart.resize()——flex 链分配高度晚于
 * ECharts 首次渲染，不手动 resize 会出现图表溢出面板（坐标轴画出边框）。
 */
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import Panel from './dashboard/Panel';

interface ChartCardProps {
  title: string;
  option: EChartsOption;
  /** 图表高度（px），默认 300；fillHeight=true 时忽略（撑满父容器） */
  height?: number;
  /** true = 图表撑满父 flex 容器（一屏自适应布局用），父链须有确定高度 */
  fillHeight?: boolean;
  /** 透传给 Panel 根节点（布局类，如 min-h-0 flex-1） */
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
  height = 300,
  fillHeight = false,
  className,
  mock = false,
  extra,
  children,
}: ChartCardProps) {
  const chartRef = useRef<ReactECharts>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  // fillHeight：flex 高度分配/窗口变化时主动 resize（ECharts 只自动监听 window resize）
  useEffect(() => {
    if (!fillHeight || !wrapRef.current) return;
    const ro = new ResizeObserver(() => chartRef.current?.getEchartsInstance().resize());
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [fillHeight]);

  const chart = (
    <ReactECharts
      ref={chartRef}
      option={option}
      className="w-full"
      // 高度属图表容器固有属性，非颜色/排版样式
      style={fillHeight ? { height: '100%' } : { height }}
      notMerge
    />
  );

  return (
    <Panel title={title} mock={mock} extra={extra} fill={fillHeight} className={className}>
      {children && <div className="mb-2 shrink-0">{children}</div>}
      {fillHeight ? (
        <div ref={wrapRef} className="min-h-0 flex-1">
          {chart}
        </div>
      ) : (
        chart
      )}
    </Panel>
  );
}
