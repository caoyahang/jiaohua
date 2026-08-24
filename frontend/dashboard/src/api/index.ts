/**
 * 接口统一入口：页面只从这里取数，不直接 fetch。
 * mock 降级约定见 client.ts；mock 数据见 mock.ts。
 */
import { request, ApiError, BackendUnreachableError } from './client';
import {
  mockFurnaceTemp,
  mockKCoefficients,
  mockOverviewKpi,
  mockPdmAlarms,
  mockQualityBoard,
  mockVisionAlarms,
} from './mock';
import type {
  FurnaceTempResponse,
  KCoefficientsResponse,
  OverviewKpi,
  PdmAlarmsResponse,
  QualityBoardResponse,
  TokenResponse,
  VisionAlarmsResponse,
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

/** 热工 K 系数（GET /furnace/k-coefficients）：后端恒 503，必走 mock */
export function getKCoefficients(
  furnaceId = 1,
): Promise<KCoefficientsResponse & { __mock?: true }> {
  return request(
    '/furnace/k-coefficients',
    { method: 'GET', query: { furnace_id: furnaceId } },
    () => mockKCoefficients(furnaceId),
  );
}

/** 实时炉温快照（GET /furnace/temp）：后端恒 503，必走 mock */
export function getFurnaceTemp(
  furnaceId = 1,
): Promise<FurnaceTempResponse & { __mock?: true }> {
  return request(
    '/furnace/temp',
    { method: 'GET', query: { furnace_id: furnaceId } },
    () => mockFurnaceTemp(furnaceId),
  );
}

/** 视觉告警（GET /vision/alarms 真实查询 vision_alarm 表）：503/断网 → client 降级 mock */
export function getVisionAlarms(
  limit = 50,
): Promise<VisionAlarmsResponse & { __mock?: true }> {
  return request(
    '/vision/alarms',
    { method: 'GET', query: { limit } },
    () => mockVisionAlarms(),
  );
}

/** PdM 告警（GET /pdm/alarms 真实查询 pdm_alarm 表）：503/断网 → client 降级 mock */
export function getPdmAlarms(
  limit = 50,
): Promise<PdmAlarmsResponse & { __mock?: true }> {
  return request(
    '/pdm/alarms',
    { method: 'GET', query: { limit } },
    () => mockPdmAlarms(),
  );
}

/**
 * 全厂汇总 KPI：后端尚无聚合接口，固定 mock 并常挂 __mock（README 接口清单）。
 * TODO：待 services/api 新增汇总接口后改为 request(...) 调用。
 */
export function getOverviewKpi(): Promise<OverviewKpi & { __mock?: true }> {
  return Promise.resolve({ ...mockOverviewKpi(), __mock: true as const });
}

/**
 * 质量看板：后端无 coke_quality 查询接口，固定 mock 并常挂 __mock。
 * TODO：待后端新增 coke_quality 查询接口后改为 request(...) 调用。
 */
export function getQualityBoard(): Promise<QualityBoardResponse & { __mock?: true }> {
  return Promise.resolve({ ...mockQualityBoard(), __mock: true as const });
}
