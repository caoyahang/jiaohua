/**
 * 登录状态 store（zustand）。
 * 中间件按前端规范固定三件套：persist（登录态持久化）+ devtools + subscribeWithSelector。
 */
import { create } from 'zustand';
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware';

interface AuthState {
  /** 后端签发的 JWT；演示模式下为 null */
  token: string | null;
  username: string | null;
  /** 演示模式：后端不可达时的纯前端演示，所有数据均挂「演示数据」角标 */
  demo: boolean;
  /** 真实登录成功 */
  login: (token: string, username: string) => void;
  /** 进入演示模式 */
  enterDemo: () => void;
  /** 退出登录 / 退出演示模式 */
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      subscribeWithSelector((set) => ({
        token: null,
        username: null,
        demo: false,
        login: (token, username) =>
          set({ token, username, demo: false }, false, 'login'),
        enterDemo: () =>
          set({ token: null, username: null, demo: true }, false, 'enterDemo'),
        logout: () =>
          set({ token: null, username: null, demo: false }, false, 'logout'),
      })),
      { name: 'pdm_ui_auth' },
    ),
    { name: 'pdm_ui_auth' },
  ),
);
