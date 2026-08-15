/**
 * 应用入口：AntD 中文化 + 深色主题（darkAlgorithm）+ OverlayScrollbars 全局初始化。
 * 大屏深色 token 与 Tailwind 同源（src/styles/tokens.ts）。
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { OverlayScrollbars } from 'overlayscrollbars';
import 'overlayscrollbars/overlayscrollbars.css';
import App from './App';
import { colors, darkColors } from './styles/tokens';
import './styles/global.scss';

// 全局统一滚动条（前端规范：滚动区域统一封装）
OverlayScrollbars(document.body, {
  scrollbars: { autoHide: 'leave' },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        // 深色大屏：darkAlgorithm + 深色 token 覆盖
        algorithm: antdTheme.darkAlgorithm,
        token: {
          colorPrimary: colors.primary,
          colorSuccess: colors.success,
          colorWarning: colors.warning,
          colorError: darkColors.alarmRed,
          colorInfo: colors.info,
          colorBgLayout: darkColors.bgPage,
          colorBgContainer: darkColors.bgCard,
          colorText: darkColors.text,
          colorTextSecondary: darkColors.textSecondary,
          colorBorder: darkColors.border,
          colorBorderSecondary: darkColors.gridLine,
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
