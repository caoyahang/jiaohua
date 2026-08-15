/**
 * Playwright 冒烟用例（前端规范§6：新页面必配）。
 * 跑在无后端环境（vite preview + 演示模式）。
 */
import { expect, test } from '@playwright/test';

test('登录页渲染：标题、账号密码框、登录按钮可见', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('智能配煤系统')).toBeVisible();
  await expect(page.getByPlaceholder('账号')).toBeVisible();
  await expect(page.getByPlaceholder('密码')).toBeVisible();
  await expect(page.getByRole('button', { name: '登 录' })).toBeVisible();
});

test('演示模式登录后进入方案优化页，生成方案出现三张卡片', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  // 无后端环境：登录请求失败后出现演示模式入口
  await page.getByRole('button', { name: '进入演示模式' }).click();
  await page.waitForURL('**/optimize');

  await page.getByRole('button', { name: '生成方案' }).click();
  // 三套方案卡片：成本最优 / 质量最稳 / 综合推荐
  await expect(page.getByText('成本最优')).toBeVisible();
  await expect(page.getByText('质量最稳')).toBeVisible();
  await expect(page.getByText('综合推荐')).toBeVisible();
});
