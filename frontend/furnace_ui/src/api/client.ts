/**
 * fetch 封装 + mock 降级约定（四模块统一样板，其他模块照抄）。
 *
 * request<T>(path, opts, mockFn?) 行为约定：
 * - 自动带 Authorization: Bearer <token>（从 auth store 取）
 * - 2xx（JSON）        → 返回真实数据
 * - 网络异常 / HTTP 503 → 有 mockFn 时降级；无 mockFn 时抛错（控制写操作严禁 mock 成功）
 * - HTTP 401            → 清 token 跳登录页
 * - 其他 4xx/5xx        → 抛带 detail 的 ApiError，页面用 AntD message/Alert 展示
 * - 非 JSON 响应         → 视为后端不可达（静态预览服务器会回退 index.html），走 mock
 */
import { useAuthStore } from '../stores/auth';

/** 带 HTTP 状态码的接口错误，detail 取自后端响应体 */
export class ApiError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** 后端不可达（网络异常/非 JSON 响应），登录接口据此提示进入演示模式 */
export class BackendUnreachableError extends Error {
  constructor() {
    super('后端服务不可达');
    this.name = 'BackendUnreachableError';
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  query?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

function isJson(resp: Response): boolean {
  return resp.headers.get('content-type')?.includes('application/json') ?? false;
}

/** 从错误响应体中提取 detail 字段 */
async function readDetail(resp: Response): Promise<string> {
  try {
    const data: unknown = await resp.json();
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail;
      return typeof detail === 'string' ? detail : JSON.stringify(detail);
    }
  } catch {
    // 响应体不是 JSON 时退化为状态码描述
  }
  return `HTTP ${resp.status}`;
}

function withMock<T extends object>(mockFn: () => T): T & { __mock: true } {
  return { ...mockFn(), __mock: true };
}

/**
 * 统一请求入口。mockFn 只在允许降级的只读/演示场景传入；控制写操作不得传入。
 */
export async function request<T extends object>(
  path: string,
  opts: RequestOptions,
  mockFn?: () => T,
): Promise<T & { __mock?: true }> {
  const { token, logout } = useAuthStore.getState();
  let resp: Response;
  try {
    resp = await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? (opts.body !== undefined ? 'POST' : 'GET'),
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    if (mockFn) return withMock(mockFn);
    throw new BackendUnreachableError();
  }
  if (!isJson(resp)) {
    // 静态预览/网关回退 HTML：401 仍需登出，其余按不可达降级 mock
    if (resp.status === 401) {
      logout();
      window.location.assign('/login');
      throw new ApiError(401, '登录已失效，请重新登录');
    }
    if (mockFn) return withMock(mockFn);
    throw new BackendUnreachableError();
  }
  if (resp.status === 401) {
    logout();
    window.location.assign('/login');
    throw new ApiError(401, '登录已失效，请重新登录');
  }
  if (resp.status === 503) {
    if (mockFn) return withMock(mockFn);
    throw new ApiError(resp.status, await readDetail(resp));
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, await readDetail(resp));
  }
  return (await resp.json()) as T;
}
