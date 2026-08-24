/**
 * @jiaminghi/data-view-react@1.2.5 本地类型声明（包本体未带 d.ts）。
 * 只声明本项目用到的 4 个组件，props 以包内 src 源码的 propTypes 为准。
 */
declare module '@jiaminghi/data-view-react' {
  import type { CSSProperties, ReactNode } from 'react';

  /** DataV 组件公共 props：style 属组件接口（传尺寸/颜色），颜色一律走 token */
  interface DataVCommonProps {
    className?: string;
    style?: CSSProperties;
  }

  /** BorderBox 系（8/10/12 接口一致）：color=[底色, 亮色] */
  export interface BorderBoxProps extends DataVCommonProps {
    children?: ReactNode;
    color?: string[];
    dur?: number;
    backgroundColor?: string;
    reverse?: boolean;
  }

  /** Decoration 系（Decoration8 用到的接口） */
  export interface DecorationProps extends DataVCommonProps {
    reverse?: boolean;
    dur?: number;
    color?: string[];
  }

  /** DigitalFlop 数字翻牌器配置（{nt}=千分位数字占位符） */
  export interface DigitalFlopConfig {
    number?: number[];
    content?: string;
    toFixed?: number;
    textAlign?: 'left' | 'center' | 'right';
    rowGap?: number;
    style?: { fontSize?: number; fill?: string; fontWeight?: number | string };
    formatter?: (n: number | string) => string;
    animationCurve?: string;
    animationFrame?: number;
  }

  export interface DigitalFlopProps extends DataVCommonProps {
    config?: DigitalFlopConfig;
  }

  /**
   * ScrollBoard 轮播表配置。
   * 注意：data 单元格经 dangerouslySetInnerHTML 渲染，业务侧必须先转义再拼高亮 span。
   */
  export interface ScrollBoardConfig {
    header?: string[];
    data?: string[][];
    rowNum?: number;
    headerBGC?: string;
    oddRowBGC?: string;
    evenRowBGC?: string;
    waitTime?: number;
    headerHeight?: number;
    columnWidth?: number[];
    align?: ('left' | 'center' | 'right')[];
    index?: boolean;
    indexHeader?: string;
    carousel?: 'single' | 'page';
    /** 悬停暂停（默认 true） */
    hoverPause?: boolean;
  }

  export interface ScrollBoardProps extends DataVCommonProps {
    config?: ScrollBoardConfig;
    onClick?: (e: { row: string[]; ceil: string; rowIndex: number; columnIndex: number }) => void;
    onMouseOver?: (e: { row: string[]; ceil: string; rowIndex: number; columnIndex: number }) => void;
  }

  export const BorderBox8: React.FC<BorderBoxProps>;
  export const BorderBox10: React.FC<BorderBoxProps>;
  export const BorderBox12: React.FC<BorderBoxProps>;
  export const Decoration5: React.FC<DecorationProps>;
  export const Decoration8: React.FC<DecorationProps>;
  export const DigitalFlop: React.FC<DigitalFlopProps>;
  export const ScrollBoard: React.FC<ScrollBoardProps>;
}
