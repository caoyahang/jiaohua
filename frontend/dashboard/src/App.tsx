/**
 * 运营总览应用外壳（方案§7.2 阶段六）。
 * 登录页直出，其余页面使用统一的浅色管理页面背景。
 */
import { BrowserRouter, useLocation } from 'react-router-dom';
import AppRoutes from './router';

function Shell() {
  const location = useLocation();

  // 登录页使用独立的居中登录布局。
  if (location.pathname === '/login') {
    return <AppRoutes />;
  }

  return (
    <div className="min-h-full bg-bgPage">
      <AppRoutes />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
