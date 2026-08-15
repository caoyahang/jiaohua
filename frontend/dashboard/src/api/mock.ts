/**
 * 演示数据（mock）：全部符合 api/types.ts 的类型，页面拿到后必须挂「演示数据」角标。
 * 响应结构以 services/api/routes/ 代码为准；后端补 response_model 后对齐 schema。
 */
import type {
  KCoefficientRow,
  KCoefficientsResponse,
  OverviewKpi,
  PdmAlarm,
  PdmAlarmsResponse,
  QualityBatch,
  QualityBoardResponse,
  VisionAlarm,
  VisionAlarmsResponse,
  VisionScene,
} from './types';

/** 固定基准日，保证 mock 可复现（不与真实时钟耦合） */
const BASE = Date.UTC(2026, 7, 14); // 2026-08-14
const DAY = 86_400_000;

function dateStr(offsetDays: number): string {
  return new Date(BASE - offsetDays * DAY).toISOString().slice(0, 10);
}

function tsStr(offsetMinutes: number): string {
  return new Date(BASE - offsetMinutes * 60_000).toISOString();
}

const SHIFTS = ['早班', '中班', '晚班'] as const;

/**
 * GET /furnace/k-coefficients 的 mock（后端恒 503，必走此分支）。
 * 近 7 天 × 三班；K3 由 K1×K2 计算并保留 3 位小数，保证恒等式在 1e-3 内成立。
 */
export function mockKCoefficients(furnaceId = 1): KCoefficientsResponse {
  const round3 = (v: number) => Math.round(v * 1000) / 1000;
  const rows: KCoefficientRow[] = [];
  for (let d = 6; d >= 0; d -= 1) {
    SHIFTS.forEach((shift, s) => {
      // 伪随机但确定性的波动：以日期+班次为种子
      const seed = d * 3 + s;
      const k1 = round3(0.93 + ((seed * 7) % 9) / 100); // 0.93~1.01
      const k2 = round3(0.95 + ((seed * 5) % 7) / 100); // 0.95~1.01
      rows.push({
        furnace_id: furnaceId,
        shift_date: dateStr(d),
        shift,
        k_uniform: round3(0.86 + ((seed * 11) % 10) / 100), // 0.86~0.95，围绕目标 0.90 波动
        k_stable: round3(0.88 + ((seed * 13) % 9) / 100),
        k1,
        k2,
        k3: round3(k1 * k2),
      });
    });
  }
  return { coefficients: rows };
}

/** GET /vision/alarms 的 mock（占位空表/不可达时降级） */
export function mockVisionAlarms(): VisionAlarmsResponse {
  const scenes: { scene: VisionScene; area: string; camera: string }[] = [
    { scene: 'helmet', area: '1#焦炉炉顶', camera: 'CAM-A01' },
    { scene: 'fire_smoke', area: '煤塔皮带廊', camera: 'CAM-B07' },
    { scene: 'intrusion', area: '煤气净化车间', camera: 'CAM-C03' },
    { scene: 'gas_leak', area: '鼓冷工段', camera: 'CAM-D02' },
    { scene: 'helmet', area: '2#焦炉机侧', camera: 'CAM-A05' },
    { scene: 'intrusion', area: '干熄焦提升井', camera: 'CAM-E01' },
    { scene: 'fire_smoke', area: '备煤车间', camera: 'CAM-B02' },
    { scene: 'helmet', area: '筛焦楼', camera: 'CAM-F04' },
    { scene: 'gas_leak', area: '脱硫工序', camera: 'CAM-D06' },
    { scene: 'intrusion', area: '1#焦炉焦侧', camera: 'CAM-A09' },
    { scene: 'helmet', area: '装煤平台', camera: 'CAM-A12' },
    { scene: 'fire_smoke', area: '运焦皮带', camera: 'CAM-B11' },
  ];
  const alarms: VisionAlarm[] = scenes.map((s, i) => ({
    alarm_id: 9001 + i,
    scene: s.scene,
    area: s.area,
    camera_id: s.camera,
    confidence: Math.round((0.78 + ((i * 7) % 20) / 100) * 100) / 100,
    ts: tsStr(i * 47 + 15),
    // 前 5 条未确认，其余已确认
    acknowledged: i >= 5,
  }));
  return { alarms };
}

/** GET /pdm/alarms 的 mock（占位空表/不可达时降级） */
export function mockPdmAlarms(): PdmAlarmsResponse {
  const defs: { equipment_id: string; level: PdmAlarm['level']; msg: string }[] = [
    { equipment_id: 'cdq_fan', level: 'DANGER', msg: '干熄焦循环风机轴承温度 78℃ 超上限' },
    { equipment_id: 'pusher_travel', level: 'WARNING', msg: '推焦车走行机构振动烈度上升趋势' },
    { equipment_id: 'gas_blower', level: 'WARNING', msg: '煤气鼓风机轴承温度偏高，建议巡检' },
    { equipment_id: 'guide_grid', level: 'DANGER', msg: '拦焦车导焦栅位移量异常增大' },
    { equipment_id: 'coal_screw', level: 'WARNING', msg: '装煤车螺旋给料电流波动超限' },
    { equipment_id: 'chem_pump', level: 'WARNING', msg: '化产离心泵密封温度缓升' },
  ];
  const alarms: PdmAlarm[] = defs.map((d, i) => ({
    alarm_id: 7001 + i,
    equipment_id: d.equipment_id,
    level: d.level,
    msg: d.msg,
    ts: tsStr(i * 83 + 30),
    // 前 4 条未确认
    acknowledged: i >= 4,
  }));
  return { alarms };
}

/**
 * 全厂汇总 KPI 的固定 mock。
 * TODO：后端尚无聚合接口（成本节约/预测准确率/煤气消耗/非计划停机），
 * 待 services/api 新增 /overview/kpi 类接口后改为 request(...) 调用。
 */
export function mockOverviewKpi(): OverviewKpi {
  return {
    cost_saving_wan: 126.8,
    quality_accuracy_pct: 87.5,
    gas_consumption_m3h: 15420,
    unplanned_stops: 2,
  };
}

/**
 * 质量看板的固定 mock（近 10 批次实测 vs AI 预测）。
 * TODO：待后端新增 coke_quality 查询接口后接通
 * （字段已对齐 data/schemas/postgresql.sql coke_quality 表 m25/pred_m25 等）。
 */
export function mockQualityBoard(): QualityBoardResponse {
  const batches: QualityBatch[] = [];
  for (let i = 9; i >= 0; i -= 1) {
    const seed = (9 - i) * 13;
    const m25 = Math.round((88.5 + ((seed * 7) % 40) / 10) * 10) / 10;
    const m10 = Math.round((6.8 - ((seed * 3) % 12) / 10) * 10) / 10;
    const csr = Math.round((62 + ((seed * 11) % 50) / 10) * 10) / 10;
    const cri = Math.round((26 - ((seed * 5) % 30) / 10) * 10) / 10;
    // 预测值围绕实测值小幅偏移，体现「实测 vs 预测」对比
    batches.push({
      batch_no: `PB202608${String(14 - i).padStart(2, '0')}-01`,
      m25,
      pred_m25: Math.round((m25 + ((seed % 7) - 3) / 10) * 10) / 10,
      m10,
      pred_m10: Math.round((m10 + ((seed % 5) - 2) / 10) * 10) / 10,
      csr,
      pred_csr: Math.round((csr + ((seed % 9) - 4) / 10) * 10) / 10,
      cri,
      pred_cri: Math.round((cri + ((seed % 6) - 3) / 10) * 10) / 10,
    });
  }
  return { batches };
}
