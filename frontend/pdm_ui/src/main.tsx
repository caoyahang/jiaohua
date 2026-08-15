/**
 * 应用入口：AntD 中文化 + 主题 token + OverlayScrollbars 全局初始化。
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { OverlayScrollbars } from 'overlayscrollbars';
import 'overlayscrollbars/overlayscrollbars.css';
import App from './App';
import { colors } from './styles/tokens';
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
        algorithm: antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: colors.primary,
          colorSuccess: colors.success,
          colorWarning: colors.warning,
          colorError: colors.danger,
          colorInfo: colors.info,
          colorBgLayout: colors.bgPage,
          colorText: colors.text,
          colorTextSecondary: colors.textSecondary,
          colorBorder: colors.border,
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
