import { defineConfig, devices } from '@playwright/test';

// 冒烟测试跑在无后端环境：vite preview 起静态产物，页面走演示模式
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:4173',
  },
  webServer: {
    command: 'npm run build && npm run preview -- --port 4173 --strictPort',
    url: 'http://localhost:4173',
    // 本机已有预览服务时直接复用（不自启 CI，无需区分环境）
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
