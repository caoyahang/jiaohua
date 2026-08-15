/**
 * Playwright 冒烟用例（前端规范§6：新页面必配）。
 * 跑在无后端环境（vite preview + 演示模式）。
 */
import { expect, test } from '@playwright/test';

test('登录页渲染：标题、账号密码框、登录按钮可见', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('设备健康监测')).toBeVisible();
  await expect(page.getByPlaceholder('账号')).toBeVisible();
  await expect(page.getByPlaceholder('密码')).toBeVisible();
  await expect(page.getByRole('button', { name: '登 录' })).toBeVisible();
});

test('演示模式进入设备总览页，渲染设备表格与「演示数据」角标', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  // 无后端环境：登录请求失败后出现演示模式入口
  await page.getByRole('button', { name: '进入演示模式' }).click();
  await page.waitForURL('**/devices');

  // 运行字段 mock 补齐，恒挂演示数据角标
  await expect(page.getByText('演示数据').first()).toBeVisible();
  // 设备表格渲染出注册设备（与后端 DEVICE_REGISTRY 一致）
  await expect(page.getByText('推焦车走行机构')).toBeVisible();
  await expect(page.getByText('皮带输送机')).toBeVisible();
});
