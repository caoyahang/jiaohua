/**
 * Playwright 冒烟用例（前端规范§6：新页面必配）。
 * 跑在无后端环境（vite preview + 演示模式）。
 */
import { expect, test } from '@playwright/test';

test('登录页渲染：标题、账号密码框、登录按钮可见', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('焦炉AI加热控制')).toBeVisible();
  await expect(page.getByPlaceholder('账号')).toBeVisible();
  await expect(page.getByPlaceholder('密码')).toBeVisible();
  await expect(page.getByRole('button', { name: '登 录' })).toBeVisible();
});

test('演示模式进入后炉温监控页渲染出图表与「演示数据」角标', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  // 无后端环境：登录请求失败后出现演示模式入口
  await page.getByRole('button', { name: '进入演示模式' }).click();
  await page.waitForURL('**/temp');

  // 图表容器渲染（ECharts canvas）与「演示数据」角标
  await expect(page.getByText('机/焦侧火道温度（℃）')).toBeVisible();
  await expect(page.locator('.ant-card canvas').first()).toBeVisible();
  await expect(page.getByText('演示数据').first()).toBeVisible();
  // 控制模式徽标全站常显
  await expect(page.getByText('控制模式：手动')).toBeVisible();
});

test('控制模式软切换不提供 manual，后端不可达时不得显示成功', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  await page.getByRole('button', { name: '进入演示模式' }).click();
  await page.goto('/control-mode');

  await page.getByLabel('目标模式').click();
  await expect(page.getByText('影子（shadow）')).toBeVisible();
  await expect(page.getByText('自动（auto）')).toBeVisible();
  await expect(page.getByText('手动（manual）')).toHaveCount(0);
  await page.getByText('影子（shadow）').click();
  await page.getByLabel('操作人（工号/姓名）').fill('operator01');
  await page.getByLabel('复核人（工号/姓名，不得与操作人相同）').fill('reviewer02');
  await page.getByLabel('切换原因').fill('影子模式验证');
  await page.getByRole('button', { name: '提交切换' }).click();
  await page.getByRole('button', { name: '确认切换' }).click();

  await expect(page.getByText('切换失败，请重试')).toBeVisible();
  await expect(page.getByText('控制模式：手动')).toBeVisible();
});
