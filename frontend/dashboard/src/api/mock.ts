/**
 * 演示数据（mock）：全部符合 api/types.ts 的类型，页面拿到后必须挂「演示数据」角标。
 * 响应结构以 services/api/routes/ 代码为准；后端补 response_model 后对齐 schema。
 */
import type {
  BurnerSide,
  FurnaceTempResponse,
  KCoefficientRow,
  KCoefficientsResponse,
  OverviewKpi,
  PdmAlarm,
  PdmAlarmsResponse,
  QualityBatch,
  QualityBoardResponse,
  TempPoint,
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

/** GET /vision/alarms 的 mock（503/断网时降级，形状与契约一致：items 数组） */
export function mockVisionAlarms(): VisionAlarmsResponse {
  const scenes: { scene: VisionScene; area: string; camera: string; label: string }[] = [
    { scene: 'helmet', area: '1#焦炉炉顶', camera: 'CAM-A01', label: 'no_helmet' },
    { scene: 'fire', area: '煤塔皮带廊', camera: 'CAM-B07', label: 'smoke' },
    { scene: 'intrusion', area: '煤气净化车间', camera: 'CAM-C03', label: 'person' },
    { scene: 'gas_leak', area: '鼓冷工段', camera: 'CAM-D02', label: 'leak_cloud' },
    { scene: 'helmet', area: '2#焦炉机侧', camera: 'CAM-A05', label: 'no_helmet' },
    { scene: 'intrusion', area: '干熄焦提升井', camera: 'CAM-E01', label: 'person' },
    { scene: 'fire', area: '备煤车间', camera: 'CAM-B02', label: 'flame' },
    { scene: 'helmet', area: '筛焦楼', camera: 'CAM-F04', label: 'no_helmet' },
    { scene: 'gas_leak', area: '脱硫工序', camera: 'CAM-D06', label: 'leak_cloud' },
    { scene: 'intrusion', area: '1#焦炉焦侧', camera: 'CAM-A09', label: 'person' },
    { scene: 'helmet', area: '装煤平台', camera: 'CAM-A12', label: 'no_helmet' },
    { scene: 'fire', area: '运焦皮带', camera: 'CAM-B11', label: 'smoke' },
  ];
  const items: VisionAlarm[] = scenes.map((s, i) => ({
    alarm_id: 9001 + i,
    scene: s.scene,
    area: s.area,
    camera_id: s.camera,
    label: s.label,
    confidence: Math.round((0.78 + ((i * 7) % 20) / 100) * 100) / 100,
    level: s.scene === 'fire' || s.scene === 'gas_leak' ? 'DANGER' : 'WARNING',
    msg: null,
    snapshot_url: null,
    ts: tsStr(i * 47 + 15),
    // 前 5 条未确认，其余已确认
    acknowledged: i >= 5,
    is_false_positive: false,
  }));
  return { items };
}

/** GET /pdm/alarms 的 mock（503/断网时降级，形状与契约一致：items 数组） */
export function mockPdmAlarms(): PdmAlarmsResponse {
  const defs: {
    equipment_id: number;
    level: PdmAlarm['level'];
    source: PdmAlarm['source'];
    msg: string;
  }[] = [
    { equipment_id: 103, level: 'DANGER', source: 'level2_trend_forecast', msg: '干熄焦循环风机轴承温度 78℃ 超上限' },
    { equipment_id: 101, level: 'WARNING', source: 'level2_trend_forecast', msg: '推焦车走行机构振动烈度上升趋势' },
    { equipment_id: 105, level: 'WARNING', source: 'level2_trend_forecast', msg: '煤气鼓风机轴承温度偏高，建议巡检' },
    { equipment_id: 102, level: 'DANGER', source: 'level1_anomaly', msg: '拦焦车导焦栅位移量异常增大' },
    { equipment_id: 104, level: 'WARNING', source: 'level1_anomaly', msg: '装煤车螺旋给料电流波动超限' },
    { equipment_id: 106, level: 'WARNING', source: 'level2_trend_forecast', msg: '化产离心泵密封温度缓升' },
  ];
  const items: PdmAlarm[] = defs.map((d, i) => ({
    alarm_id: 7001 + i,
    equipment_id: d.equipment_id,
    level: d.level,
    source: d.source,
    metric: null,
    metric_value: null,
    threshold: null,
    iso10816_zone: null,
    msg: d.msg,
    ts: tsStr(i * 83 + 30),
    // 前 4 条未确认
    acknowledged: i >= 4,
    handler: null,
    ack_comment: null,
    acked_at: null,
  }));
  return { items };
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
 * GET /furnace/temp 的 mock（后端恒 503，必走此分支）。
 * 机/焦侧最新一点快照，字段口径对齐 TDengine furnace_temp 表（方案§3.4.3）；
 * 数值带以当前分钟为相位的缓慢波动，模拟实时采样。
 */
export function mockFurnaceTemp(furnaceId = 1): FurnaceTempResponse {
  const now = new Date();
  const phase = (now.getMinutes() * 60 + now.getSeconds()) / 600; // 10 分钟一个慢波周期
  const round1 = (v: number) => Math.round(v * 10) / 10;
  const sides: BurnerSide[] = ['machine', 'coke'];
  const points: TempPoint[] = sides.map((side, i) => ({
    ts: now.toISOString(),
    burner_side: side,
    // 火道温度 1180~1250℃，机侧略低于焦侧
    fire_channel_temp: round1(1215 + (i === 0 ? -8 : 8) + Math.sin(phase + i * 1.3) * 18),
    gas_flow: Math.round(15420 + Math.sin(phase) * 260),
    flue_suction: round1(-165 + Math.sin(phase + 0.6) * 8),
    collector_pressure: round1(105 + Math.sin(phase + 0.9) * 6),
    oxygen_content: round1(5.6 + Math.sin(phase + 1.7) * 0.8),
    control_mode: 'manual',
    switching: false,
  }));
  return { furnace_id: furnaceId, points };
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
