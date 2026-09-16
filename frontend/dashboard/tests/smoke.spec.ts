/**
 * Playwright 冒烟用例（前端规范§6：新页面必配）。
 * 用路由拦截模拟无后端环境（本机可能跑着真实 FastAPI，直接访问会真登录成功），
 * 使「演示模式 + 全区块 mock 降级」路径在任何环境下确定可测。
 */
import { expect, test } from '@playwright/test';

/** 拦截全部后端 API 请求并中断：等价于后端不可达 */
async function mockBackendDown(page: import('@playwright/test').Page) {
  await page.route(/\/(auth|blend|furnace|pdm|vision)\//, (route) => route.abort());
}

test('登录页渲染：标题、账号密码框、登录按钮可见', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('焦化厂智能化平台 · 运营总览')).toBeVisible();
  await expect(page.getByPlaceholder('账号')).toBeVisible();
  await expect(page.getByPlaceholder('密码')).toBeVisible();
  await expect(page.getByRole('button', { name: '登 录' })).toBeVisible();
});

test('演示模式进入运营总览，KPI、趋势与告警表格渲染', async ({ page }) => {
  await mockBackendDown(page);
  await page.goto('/login');
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  // 无后端环境：登录请求失败后出现演示模式入口
  await page.getByRole('button', { name: '进入演示模式' }).click();
  await page.waitForURL('**/');

  // 常规顶部导航与页面标题
  await expect(page.getByText('焦化厂智能化平台', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '运营总览' })).toBeVisible();
  await expect(page.getByRole('button', { name: /刷新/ })).toBeVisible();
  // KPI 卡片区
  await expect(page.getByText('本月配煤成本节约')).toBeVisible();
  await expect(page.getByText('未确认安全告警')).toBeVisible();
  // 趋势、质量、安全与告警表格
  await expect(page.getByText('热工稳定性趋势（K均 / K安）')).toBeVisible();
  await expect(page.getByText('推焦执行趋势（K1 / K2 / K3）')).toBeVisible();
  await expect(page.getByText('焦炭质量趋势：实测与 AI 预测')).toBeVisible();
  await expect(page.getByText('安全与设备告警')).toBeVisible();
  await expect(page.getByText('最新视觉告警')).toBeVisible();
  await expect(page.getByRole('columnheader', { name: '告警内容' })).toBeVisible();
  // ECharts 图表容器已挂载
  await expect(page.locator('.echarts-for-react').first()).toBeVisible();
  // 页面不再加载 DataV 驾驶舱组件。
  await expect(page.locator('[class*="dv-"]')).toHaveCount(0);
});
