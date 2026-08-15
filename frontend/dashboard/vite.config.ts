import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 开发代理：前端直连本机 8000 端口的 FastAPI 后端（services/api）
export default defineConfig({
  plugins: [react()],
  server: {
    // 本模块端口 5174（blend_ui 占 5173），代理 /auth /blend /furnace /pdm /vision → FastAPI
    port: 5174,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/blend': 'http://localhost:8000',
      '/furnace': 'http://localhost:8000',
      '/pdm': 'http://localhost:8000',
      '/vision': 'http://localhost:8000',
    },
  },
});
