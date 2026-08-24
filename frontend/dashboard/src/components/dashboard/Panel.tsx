/**
 * 大屏面板容器：DataV 科技风边框 + 标题左侧色条。
 * 边框两种：bb12 四角括号呼吸辉光（默认）/ bb8 流光跑边（中央示意等重点面板）。
 * BorderBox 作为 absolute 边框层铺满面板，内容层保持自动高度；
 * fill=true 时面板撑满父容器（h-full flex 列，供一屏自适应布局使用）。
 * 颜色全部取 darkColors token（红线4）。
 */
import type { ReactNode } from 'react';
import { BorderBox8, BorderBox12 } from '@jiaminghi/data-view-react';
import MockBadge from '../MockBadge';
import { darkColors } from '../../styles/tokens';
import { BorderLayer } from './screen.styled';

interface PanelProps {
  /** 面板标题；不传则不渲染标题栏 */
  title?: string;
  /** 数据源为 mock 时传 true，标题旁显示「演示数据」角标 */
  mock?: boolean;
  /** 标题栏右侧附加内容（如 Segmented 切换器） */
  extra?: ReactNode;
  /** 边框样式：bb12（默认）/ bb8（流光跑边，更醒目） */
  border?: 'bb12' | 'bb8';
  /** true = 面板撑满父容器高度（flex 链传给内容层） */
  fill?: boolean;
  children: ReactNode;
  className?: string;
}

export default function Panel({
  title,
  mock = false,
  extra,
  border = 'bb12',
  fill = false,
  children,
  className,
}: PanelProps) {
  const BorderBox = border === 'bb8' ? BorderBox8 : BorderBox12;
  return (
    <section
      className={`relative bg-darkCard/70 ${fill ? 'flex h-full min-h-0 flex-col' : ''} ${className ?? ''}`}
    >
      {/* DataV 边框层：BorderLayer（styled）absolute 铺满，随面板内容高度自适应 */}
      <BorderLayer>
        <BorderBox color={[darkColors.accentCyanDim, darkColors.accentCyan]} />
      </BorderLayer>
      <div className={`relative ${fill ? 'flex min-h-0 flex-1 flex-col' : ''}`}>
        {title !== undefined && (
          <header className="flex shrink-0 items-center justify-between gap-2 border-b border-darkGridLine px-3 py-2">
            <span className="flex min-w-0 items-center text-sm font-bold text-darkText">
              {/* 标题左侧色条 */}
              <span className="mr-2 h-3.5 w-1 shrink-0 bg-darkAccentCyan" />
              <span className="truncate">{title}</span>
              {mock && <MockBadge />}
            </span>
            {extra}
          </header>
        )}
        <div className={`p-3 ${fill ? 'flex min-h-0 flex-1 flex-col' : ''}`}>{children}</div>
      </div>
    </section>
  );
}
