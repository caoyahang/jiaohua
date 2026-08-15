/**
 * 路由表 + 未登录守卫（未登录一律跳 /login）。
 */
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuthStore } from './stores/auth';
import LoginPage from './pages/LoginPage';
import TempMonitorPage from './pages/TempMonitorPage';
import AiSetpointPage from './pages/AiSetpointPage';
import ControlModePage from './pages/ControlModePage';
import KCoeffPage from './pages/KCoeffPage';

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
        path="/temp"
        element={
          <RequireAuth>
            <TempMonitorPage />
          </RequireAuth>
        }
      />
      <Route
        path="/ai-setpoint"
        element={
          <RequireAuth>
            <AiSetpointPage />
          </RequireAuth>
        }
      />
      <Route
        path="/control-mode"
        element={
          <RequireAuth>
            <ControlModePage />
          </RequireAuth>
        }
      />
      <Route
        path="/k-coeff"
        element={
          <RequireAuth>
            <KCoeffPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/temp" replace />} />
    </Routes>
  );
}
