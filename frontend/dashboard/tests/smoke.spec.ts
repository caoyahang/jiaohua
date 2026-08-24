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
  await expect(page.getByText('焦化厂智能化平台 · 领导驾驶舱')).toBeVisible();
  await expect(page.getByPlaceholder('账号')).toBeVisible();
  await expect(page.getByPlaceholder('密码')).toBeVisible();
  await expect(page.getByRole('button', { name: '登 录' })).toBeVisible();
});

test('演示模式进入大屏页，KPI 卡片与图表容器渲染', async ({ page }) => {
  await mockBackendDown(page);
  await page.goto('/login');
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  // 无后端环境：登录请求失败后出现演示模式入口
  await page.getByRole('button', { name: '进入演示模式' }).click();
  await page.waitForURL('**/');

  // 顶部标题栏
  await expect(page.getByText('AI焦化厂智能管控平台')).toBeVisible();
  // KPI 卡片区
  await expect(page.getByText('本月配煤成本节约')).toBeVisible();
  await expect(page.getByText('未确认安全告警')).toBeVisible();
  // 工艺示意图（GET /furnace/temp 恒 503 → mock 渲染）
  await expect(page.getByText('焦炉加热系统示意')).toBeVisible();
  await expect(page.getByText('机侧火道温度')).toBeVisible();
  await expect(page.getByText('炭化室', { exact: true })).toBeVisible();
  // 各区块卡片标题（图表容器随卡片渲染）
  await expect(page.getByText('热工 KPI：K均 / K安 近 7 天')).toBeVisible();
  await expect(page.getByText('推焦 KPI：K1 / K2 / K3 近 7 天')).toBeVisible();
  await expect(page.getByText('质量看板：实测 vs AI 预测（近 10 批次）')).toBeVisible();
  await expect(page.getByText('安全看板')).toBeVisible();
  await expect(page.getByText('视觉 AI 告警（滚动轮播，悬停暂停）')).toBeVisible();
  // ECharts 图表容器已挂载
  await expect(page.locator('.echarts-for-react').first()).toBeVisible();
  // DataV 组件已挂载（BorderBox 边框层 + ScrollBoard 轮播表）
  await expect(page.locator('.dv-border-box-12').first()).toBeVisible();
  await expect(page.locator('.dv-scroll-board')).toBeVisible();
});
