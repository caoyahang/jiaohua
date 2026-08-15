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
  // ISO 10816「不合格」区徽标/图表着色（介于注意黄与危险红之间）
  orange: '#d46b08',
  info: '#1677ff',
  // 中性色：页面背景 / 卡片背景 / 边框 / 正文 / 次要文字
  bgPage: '#f0f2f5',
  bgCard: '#ffffff',
  border: '#d9d9d9',
  text: '#262626',
  textSecondary: '#8c8c8c',
} as const;

export type ColorToken = keyof typeof colors;
