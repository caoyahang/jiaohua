/**
 * 颜色 token 唯一来源（前端规范红线4）。
 * Tailwind config 与 AntD ConfigProvider theme 均从这里取值，组件内禁止写颜色字面量。
 */

export const colors = {
  // 主色：炼焦蓝（导航、主按钮、链接）
  primary: '#1f5f8b',
  // 辅助色
  success: '#389e0d',
  warning: '#d48806',
  danger: '#cf1322',
  info: '#1677ff',
  // 中性色：页面背景 / 卡片背景 / 边框 / 正文 / 次要文字
  bgPage: '#f0f2f5',
  bgCard: '#ffffff',
  border: '#d9d9d9',
  text: '#262626',
  textSecondary: '#8c8c8c',
} as const;

/**
 * 大屏深色 token（本模块新增，原 token 不删）。
 * 领导驾驶舱整屏深色：AntD darkAlgorithm 的覆盖值与 Tailwind 类同源取这里。
 */
export const darkColors = {
  // 页面底色：深海蓝黑
  bgPage: '#0b1526',
  // 卡片底色：略高于页面底
  bgCard: '#132138',
  // 卡片描边/分割线
  border: '#24406b',
  // 高对比正文
  text: '#e8f1ff',
  // 次要文字（坐标轴、说明）
  textSecondary: '#8fa8cf',
  // 图表网格线
  gridLine: '#1d3252',
  // KPI 数值强调色
  kpiValue: '#53c1ff',
  // 目标线/告警红（比 danger 更亮，深底下可读）
  alarmRed: '#ff4d4f',
} as const;

export type DarkColorToken = keyof typeof darkColors;

export type ColorToken = keyof typeof colors;
