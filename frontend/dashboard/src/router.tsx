/**
 * 路由表 + 未登录守卫（未登录一律跳 /login）。
 * 运营总览单页：仅 /login 与 / 两条路由。
 */
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuthStore } from './stores/auth';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';

/** 登录守卫：无 token 且不在演示模式时跳登录页 */
function RequireAuth({ children }: { children: ReactNode }) {
  const { token, demo } = useAuthStore();
  const location = useLocation();
  if (!token && !demo) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <>{children}</>;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
