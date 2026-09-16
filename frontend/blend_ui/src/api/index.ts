/**
 * 接口统一入口：页面只从这里取数，不直接 fetch。
 * mock 降级约定见 client.ts；mock 数据见 mock.ts。
 */
import { request, ApiError, BackendUnreachableError } from './client';
import { mockFeedback, mockOptimize, mockPredict, mockRecipes } from './mock';
import type {
  FeedbackResponse,
  LabFeedback,
  OptimizeRequest,
  OptimizeResponse,
  PredictRequest,
  PredictResponse,
  RecipesResponse,
  TokenResponse,
} from './types';

export { ApiError, BackendUnreachableError };

/**
 * 登录（POST /auth/login，后端可用，不做 mock 降级）。
 * - 网络异常/非 JSON 响应 → 抛 BackendUnreachableError，由页面提示进入演示模式
 * - 401 → 抛 ApiError（用户名或密码错误），如实展示，不降级
 */
export async function login(
  username: string,
  password: string,
): Promise<TokenResponse> {
  let resp: Response;
  try {
    resp = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
  } catch {
    throw new BackendUnreachableError();
  }
  if (!resp.headers.get('content-type')?.includes('application/json')) {
    // 静态预览服务器无 /auth/login：视为后端不可达
    if (resp.status === 401) {
      throw new ApiError(401, '用户名或密码错误');
    }
    throw new BackendUnreachableError();
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = (await resp.json()) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      // 保留状态码描述
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as TokenResponse;
}

/** 配煤优化（POST /blend/optimize）：真实可用，依赖缺失/断网时降级 mock */
export function optimizeBlend(
  req: OptimizeRequest,
): Promise<OptimizeResponse & { __mock?: true }> {
  return request('/blend/optimize', { body: req }, () => mockOptimize(req));
}

/** 质量预测：后端暂无独立接口，纯演示实现并固定挂 __mock（README 接口清单） */
export function predictQuality(
  req: PredictRequest,
): Promise<PredictResponse & { __mock?: true }> {
  return Promise.resolve({ ...mockPredict(req), __mock: true as const });
}

/** 历史配煤方案（GET /blend/recipes）：PG 挂则 503，自动降级 mock */
export function listRecipes(
  furnaceId?: number,
  limit = 50,
): Promise<RecipesResponse & { __mock?: true }> {
  return request(
    '/blend/recipes',
    { method: 'GET', query: { furnace_id: furnaceId, limit } },
    () => mockRecipes(furnaceId),
  );
}

/** 化验结果回写（POST /blend/feedback）：后端未接通时以演示结果明确降级 */
export function submitFeedback(
  req: LabFeedback,
): Promise<FeedbackResponse & { __mock?: true }> {
  return request('/blend/feedback', { body: req }, () => mockFeedback(req));
}
