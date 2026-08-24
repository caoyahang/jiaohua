/**
 * 大屏外壳：登录页直出；其余页面（单页大屏）套深色底容器渲染路由。
 * 顶部标题栏已迁入大屏页（components/dashboard/ScreenHeader.tsx）。
 */
import { BrowserRouter, useLocation } from 'react-router-dom';
import AppRoutes from './router';

function Shell() {
  const location = useLocation();

  // 登录页不显示大屏外壳
  if (location.pathname === '/login') {
    return <AppRoutes />;
  }

  return (
    <div className="min-h-full bg-darkDeep">
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
