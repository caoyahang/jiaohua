/**
 * 路由表 + 未登录守卫（未登录一律跳 /login）。
 */
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuthStore } from './stores/auth';
import LoginPage from './pages/LoginPage';
import PredictPage from './pages/PredictPage';
import OptimizePage from './pages/OptimizePage';
import RecipesPage from './pages/RecipesPage';
import FeedbackPage from './pages/FeedbackPage';

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
        path="/predict"
        element={
          <RequireAuth>
            <PredictPage />
          </RequireAuth>
        }
      />
      <Route
        path="/optimize"
        element={
          <RequireAuth>
            <OptimizePage />
          </RequireAuth>
        }
      />
      <Route
        path="/recipes"
        element={
          <RequireAuth>
            <RecipesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/feedback"
        element={
          <RequireAuth>
            <FeedbackPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/optimize" replace />} />
    </Routes>
  );
}
