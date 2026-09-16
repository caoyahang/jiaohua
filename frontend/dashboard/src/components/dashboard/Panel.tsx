/**
 * 运营总览通用内容卡片：统一标题、演示数据角标和正文间距。
 * 依据方案§7.2 阶段六；样式采用常规管理页面卡片语义。
 */
import type { ReactNode } from 'react';
import MockBadge from '../MockBadge';

interface PanelProps {
  /** 卡片标题；不传则不渲染标题栏 */
  title?: string;
  /** 数据源为 mock 时显示「演示数据」角标 */
  mock?: boolean;
  /** 标题栏右侧附加内容 */
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function Panel({ title, mock = false, extra, children, className }: PanelProps) {
  return (
    <section className={`overflow-hidden rounded-lg border border-border bg-bgCard shadow-sm ${className ?? ''}`}>
      {title !== undefined && (
        <header className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="flex min-w-0 items-center">
            <h2 className="truncate text-sm font-semibold text-text">{title}</h2>
            {mock && <MockBadge />}
          </div>
          {extra}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
