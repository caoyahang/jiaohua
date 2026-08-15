// Tailwind 与 AntD ConfigProvider 同源引用 src/styles/tokens.ts（红线4：颜色唯一来源）
// @ts-check
/** @type {import('tailwindcss').Config} */
import { colors, darkColors } from './src/styles/tokens.ts';

// 深色 token 以 dark 前缀并入（bg 开头的键去掉 bg：bgPage→darkPage、bgCard→darkCard；
// 其余直拼：text→darkText、alarmRed→darkAlarmRed …），与原 token 共存
const dark = Object.fromEntries(
  Object.entries(darkColors).map(([k, v]) => {
    const stripped = k.startsWith('bg') ? k.slice(2) : k;
    return [`dark${stripped[0].toUpperCase()}${stripped.slice(1)}`, v];
  }),
);

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: { colors: { ...colors, ...dark } },
  },
  plugins: [],
};
