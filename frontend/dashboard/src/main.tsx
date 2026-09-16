/**
 * 应用入口：AntD 中文化、统一浅色 token 与全局滚动条初始化。
 * 依据方案§7.2 阶段六运营总览设计。
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
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
        token: {
          colorPrimary: colors.primary,
          colorSuccess: colors.success,
          colorWarning: colors.warning,
          colorError: colors.danger,
          colorInfo: colors.info,
          colorBgLayout: colors.bgPage,
          colorBgContainer: colors.bgCard,
          colorText: colors.text,
          colorTextSecondary: colors.textSecondary,
          colorBorder: colors.border,
          colorBorderSecondary: colors.border,
          borderRadius: 8,
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
