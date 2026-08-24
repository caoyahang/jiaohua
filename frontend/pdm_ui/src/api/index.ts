/**
 * 接口统一入口：页面只从这里取数，不直接 fetch。
 * mock 降级约定见 client.ts；mock 数据见 mock.ts。
 *
 * PdM 后端现状（services/api/routes/pdm.py）：
 * - /pdm/devices 真实可用但只回注册信息 → 运行字段 mock 补齐，结果恒挂 __mock
 * - /pdm/devices/{id}/health 恒 503 → client 自动降级 mock
 * - /pdm/alarms 真实查询 pdm_alarm 表（契约见 docs/API文档.md §5）；
 *   503/断网由 client 自动降级 mock
 * - PdM 无 ack 接口：告警确认为前端本地状态，见 stores/alarmAck.ts
 */
import { request, ApiError, BackendUnreachableError } from './client';
import { mockAlarms, mockDeviceRuntime, mockDevices, mockHealth } from './mock';
import type {
  AlarmsResponse,
  DevicePriority,
  DeviceRow,
  DevicesResponse,
  HealthResponse,
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

/**
 * 设备总览（GET /pdm/devices）。
 * 真实响应只有注册信息；运行字段（状态/健康评分/振动/温度）由 mock 补齐，
 * 因此无论真假都挂 __mock，页面恒显示「演示数据」角标（见 README 接口清单）。
 */
export async function listDevices(
  priority?: DevicePriority,
): Promise<{ devices: DeviceRow[]; total: number; __mock?: true }> {
  const resp = await request<DevicesResponse>(
    '/pdm/devices',
    { method: 'GET', query: { priority } },
    () => {
      const all = mockDevices();
      const devices = priority
        ? all.devices.filter((d) => d.priority === priority)
        : all.devices;
      return { devices, total: devices.length };
    },
  );
  // 降级时 mockFn 返回的就是 DeviceRow（含运行字段）；此处仅做类型收窄
  if (resp.__mock) return resp as { devices: DeviceRow[]; total: number; __mock: true };
  // 真实注册信息 + mock 运行字段
  const devices = resp.devices.map((d) => ({ ...d, ...mockDeviceRuntime(d.device_id) }));
  return { devices, total: resp.total, __mock: true };
}

/** 设备健康评分（GET /pdm/devices/{id}/health）：后端恒 503，必走 mock */
export function getDeviceHealth(
  deviceId: string,
): Promise<HealthResponse & { __mock?: true }> {
  return request(
    `/pdm/devices/${encodeURIComponent(deviceId)}/health`,
    { method: 'GET' },
    () => mockHealth(deviceId),
  );
}

/**
 * PdM 告警（GET /pdm/alarms）：真实查询 pdm_alarm 表。
 * 旧参数 device_id(string) 已改为 equipment_id(int，设备主键）；
 * 503/断网由 client 自动降级 mock（mock 形状与契约一致）。
 */
export function listAlarms(
  level?: 'WARNING' | 'DANGER',
  equipmentId?: number,
): Promise<AlarmsResponse & { __mock?: true }> {
  return request<AlarmsResponse>(
    '/pdm/alarms',
    { method: 'GET', query: { level, equipment_id: equipmentId } },
    () => {
      let items = mockAlarms().items;
      if (level) items = items.filter((a) => a.level === level);
      if (equipmentId !== undefined) items = items.filter((a) => a.equipment_id === equipmentId);
      return { items };
    },
  );
}
