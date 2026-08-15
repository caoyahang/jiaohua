/**
 * 接口统一入口：页面只从这里取数，不直接 fetch。
 * mock 降级约定见 client.ts；mock 数据见 mock.ts。
 */
import { request, ApiError, BackendUnreachableError } from './client';
import {
  mockAiSetpoint,
  mockControlMode,
  mockKCoefficients,
  mockTemp,
} from './mock';
import type {
  AiSetpointResponse,
  ControlModeRequest,
  ControlModeResponse,
  KCoeffResponse,
  TempResponse,
  TokenResponse,
} from './types';
import { useFurnaceStore } from '../stores/furnace';

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

/** 实时炉温（GET /furnace/temp）：后端恒 503，必走 mock */
export function getTemp(
  furnaceId: number,
): Promise<TempResponse & { __mock?: true }> {
  return request(
    '/furnace/temp',
    { method: 'GET', query: { furnace_id: furnaceId } },
    // mock 时序点带上当前控制模式，便于演示模式徽标联动
    () => mockTemp(furnaceId, useFurnaceStore.getState().controlMode),
  );
}

/** AI 设定值建议（GET /furnace/ai-setpoint）：真实可用，mock 仅断网兜底 */
export function getAiSetpoint(
  furnaceId: number,
): Promise<AiSetpointResponse & { __mock?: true }> {
  return request(
    '/furnace/ai-setpoint',
    { method: 'GET', query: { furnace_id: furnaceId } },
    () => mockAiSetpoint(furnaceId),
  );
}

/** 切换控制模式（POST /furnace/control-mode）：真实可用，mock 仅断网兜底 */
export function setControlMode(
  req: ControlModeRequest,
): Promise<ControlModeResponse & { __mock?: true }> {
  return request('/furnace/control-mode', { body: req }, () =>
    mockControlMode(req),
  );
}

/** 热工 K 系数（GET /furnace/k-coefficients）：后端恒 503，必走 mock */
export function getKCoefficients(
  furnaceId: number,
  shiftDate?: string,
): Promise<KCoeffResponse & { __mock?: true }> {
  return request(
    '/furnace/k-coefficients',
    {
      method: 'GET',
      query: { furnace_id: furnaceId, shift_date: shiftDate },
    },
    () => mockKCoefficients(furnaceId),
  );
}
