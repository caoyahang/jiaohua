/**
 * 演示数据（mock）：全部符合 api/types.ts 的类型，页面拿到后必须挂「演示数据」角标。
 * 响应结构以 services/api/routes/furnace.py 为准；后端补 response_model 后对齐 schema。
 * 伪随机数全部用确定性 hash，保证演示数据可复现（测试规范§4）。
 */
import type {
  AiSetpointResponse,
  BurnerSide,
  ControlMode,
  KCoeffResponse,
  KShiftRecord,
  TempPoint,
  TempResponse,
} from './types';

/** 确定性伪随机：由整数种子生成 [0,1) 小数（演示数据可复现） */
function seeded(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/** GET /furnace/temp 的 mock（后端恒 503，必走此分支）。 */
export function mockTemp(furnaceId: number, mode: ControlMode): TempResponse {
  const points: TempPoint[] = [];
  const sides: BurnerSide[] = ['machine', 'coke'];
  const now = Date.now();
  // 近 2 小时、1 分钟间隔、双侧时序（120×2=240 点）
  for (let minute = 119; minute >= 0; minute -= 1) {
    const ts = new Date(now - minute * 60_000);
    // 每 30 分钟一段 3 分钟换向期（换向前后 2~3 分钟为脏数据，方案§4.2.6）
    const switching = minute % 30 < 3;
    for (const side of sides) {
      const seed = minute * 7 + (side === 'machine' ? 1 : 2);
      // 火道温度 1180~1250℃ 波动，机侧略低于焦侧
      const base = 1215 + (side === 'machine' ? -8 : 8);
      const wave = Math.sin(minute / 9 + (side === 'machine' ? 0 : 1.3)) * 18;
      const noise = (seeded(seed) - 0.5) * 12;
      points.push({
        ts: ts.toISOString(),
        burner_side: side,
        fire_channel_temp:
          Math.round((base + wave + noise) * 10) / 10,
        gas_flow:
          Math.round(15200 + Math.sin(minute / 15) * 400 + seeded(seed + 3) * 200),
        flue_suction:
          Math.round((150 + Math.sin(minute / 20) * 12 + seeded(seed + 5) * 8) * 10) / 10,
        collector_pressure:
          Math.round((118 + Math.sin(minute / 25) * 6 + seeded(seed + 7) * 4) * 10) / 10,
        oxygen_content:
          Math.round((5.2 + Math.sin(minute / 12) * 1.2 + seeded(seed + 9)) * 100) / 100,
        control_mode: mode,
        switching,
      });
    }
  }
  return { furnace_id: furnaceId, points };
}

/** GET /furnace/ai-setpoint 的演示数据（后端模型未就绪时使用）。 */
export function mockAiSetpoint(furnaceId: number): AiSetpointResponse {
  return {
    furnace_id: furnaceId,
    gas_flow_setpoint: 15500,
    clamped: false,
    model_version: null,
  };
}

const SHIFTS = ['早班', '中班', '晚班'] as const;

/** GET /furnace/k-coefficients 的 mock（后端恒 503，必走此分支）。 */
export function mockKCoefficients(furnaceId: number): KCoeffResponse {
  const records: KShiftRecord[] = [];
  const today = new Date();
  // 近 7 天 × 早中晚三班 = 21 条
  for (let day = 6; day >= 0; day -= 1) {
    const date = new Date(today.getTime() - day * 86_400_000);
    const shiftDate = date.toISOString().slice(0, 10);
    for (let s = 0; s < SHIFTS.length; s += 1) {
      const seed = day * 11 + s * 3 + furnaceId;
      // K1/K2 取 0.86~1.00，K3=K1×K2 恒等式严格成立（红线，测试规范§4）
      const k1 = Math.round((0.86 + seeded(seed) * 0.14) * 1000) / 1000;
      const k2 = Math.round((0.88 + seeded(seed + 1) * 0.12) * 1000) / 1000;
      const k3 = Math.round(k1 * k2 * 1000) / 1000;
      records.push({
        furnace_id: furnaceId,
        shift_date: shiftDate,
        shift: SHIFTS[s],
        k_uniform: Math.round((0.84 + seeded(seed + 2) * 0.15) * 1000) / 1000,
        k_stable: Math.round((0.88 + seeded(seed + 4) * 0.11) * 1000) / 1000,
        k1,
        k2,
        k3,
      });
    }
  }
  return { records };
}
