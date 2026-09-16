// Tailwind 与 AntD ConfigProvider 同源引用 src/styles/tokens.ts（红线4：颜色唯一来源）
// @ts-check
/** @type {import('tailwindcss').Config} */
import { colors } from './src/styles/tokens.ts';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: { colors },
  },
  plugins: [],
};
