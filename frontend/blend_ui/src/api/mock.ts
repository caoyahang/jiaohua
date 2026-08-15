/**
 * 演示数据（mock）：全部符合 api/types.ts 的类型，页面拿到后必须挂「演示数据」角标。
 * 响应结构以 services/api/routes/blend.py 为准；后端补 response_model 后对齐 schema。
 */
import type {
  BlendRecipe,
  BlendSolution,
  CoalInfo,
  FeedbackResponse,
  LabFeedback,
  OptimizeRequest,
  OptimizeResponse,
  PredictRequest,
  PredictResponse,
  QualityMetrics,
  SolutionType,
} from './types';

/** 预设可用煤种（方案§4.1：气煤/肥煤/焦煤/瘦煤/1/3焦煤），Predict/Optimize 两页共用 */
export const presetCoals: CoalInfo[] = [
  {
    coal_id: 1,
    name: '气煤',
    stock_tons: 1200,
    price_per_ton: 980,
    min_ratio: 0.1,
    max_ratio: 0.4,
    lab_data: { Ad: 8.5, Vdaf: 38.2, St_d: 0.5, G: 65, Y: 12, Rmax: 0.75 },
  },
  {
    coal_id: 2,
    name: '肥煤',
    stock_tons: 800,
    price_per_ton: 1350,
    min_ratio: 0.1,
    max_ratio: 0.35,
    lab_data: { Ad: 9.2, Vdaf: 30.5, St_d: 0.6, G: 90, Y: 26, Rmax: 1.05 },
  },
  {
    coal_id: 3,
    name: '焦煤',
    stock_tons: 600,
    price_per_ton: 1580,
    min_ratio: 0.15,
    max_ratio: 0.4,
    lab_data: { Ad: 9.8, Vdaf: 24.1, St_d: 0.7, G: 82, Y: 18, Rmax: 1.35 },
  },
  {
    coal_id: 4,
    name: '瘦煤',
    stock_tons: 900,
    price_per_ton: 1120,
    min_ratio: 0,
    max_ratio: 0.3,
    lab_data: { Ad: 10.1, Vdaf: 16.8, St_d: 0.8, G: 35, Y: 6, Rmax: 1.6 },
  },
  {
    coal_id: 5,
    name: '1/3焦煤',
    stock_tons: 1000,
    price_per_ton: 1240,
    min_ratio: 0.05,
    max_ratio: 0.35,
    lab_data: { Ad: 9.0, Vdaf: 32.4, St_d: 0.55, G: 78, Y: 15, Rmax: 1.1 },
  },
];

/**
 * 在 [min_ratio, max_ratio] 约束下按权重分配配比（合计=1）。
 * 先铺下限，剩余量按权重往上限填；演示用，不做严格寻优。
 */
function distributeByWeight(
  coals: CoalInfo[],
  weightOf: (c: CoalInfo) => number,
): Record<string, number> {
  const ratios: Record<string, number> = {};
  let remaining = 1;
  for (const c of coals) {
    ratios[c.name] = c.min_ratio;
    remaining -= c.min_ratio;
  }
  // 按权重迭代填充，直至剩余量分完或全部触顶
  for (let round = 0; round < 10 && remaining > 1e-6; round += 1) {
    const open = coals.filter((c) => ratios[c.name] < c.max_ratio - 1e-6);
    if (open.length === 0) break;
    const totalWeight = open.reduce((s, c) => s + Math.max(weightOf(c), 0.01), 0);
    for (const c of open) {
      const share = (remaining * Math.max(weightOf(c), 0.01)) / totalWeight;
      const room = c.max_ratio - ratios[c.name];
      const add = Math.min(share, room);
      ratios[c.name] += add;
      remaining -= add;
    }
  }
  // 兜底：剩余量塞给第一个未触顶的煤种（理论上 Σmax>=1 时不会走到）
  if (remaining > 1e-6) {
    const c = coals.find((x) => ratios[x.name] < x.max_ratio - 1e-6);
    if (c) ratios[c.name] += remaining;
  }
  return ratios;
}

/** 由配比估算成本与质量（演示用线性经验式，系数待 DOE 标定，方案§4.1.6） */
function estimateSolution(
  coals: CoalInfo[],
  ratio: Record<string, number>,
  type: SolutionType,
): BlendSolution {
  let cost = 0;
  let gSum = 0;
  let vdafSum = 0;
  for (const c of coals) {
    const r = ratio[c.name] ?? 0;
    cost += r * c.price_per_ton;
    gSum += r * Number(c.lab_data.G ?? 0);
    vdafSum += r * Number(c.lab_data.Vdaf ?? 0);
  }
  // 经验模型：G 值高 → 强度好；Vdaf 高 → 反应性偏高
  const quality: QualityMetrics = {
    M25: Math.round((78 + gSum * 0.14) * 10) / 10,
    M10: Math.round((8.5 - gSum * 0.02) * 10) / 10,
    CSR: Math.round((48 + gSum * 0.22 - vdafSum * 0.1) * 10) / 10,
    CRI: Math.round((18 + vdafSum * 0.25 - gSum * 0.05) * 10) / 10,
  };
  const explanations: Record<SolutionType, string> = {
    cost_optimal:
      '以低价气煤/瘦煤为主，成本最低；G 值偏低，M25 余量较小，适合质量裕度充足的炉况。',
    quality_stable:
      '提高肥煤、焦煤比例，粘结性（G 值）最高，焦炭强度最稳；成本相应上升。',
    balanced:
      '成本与质量折中：主焦煤保证强度，气煤摊薄成本，综合性价比最优。',
  };
  const confidences: Record<SolutionType, number> = {
    cost_optimal: 0.62,
    quality_stable: 0.71,
    balanced: 0.68,
  };
  return {
    type,
    blend_ratio: Object.fromEntries(
      Object.entries(ratio).map(([k, v]) => [k, Math.round(v * 1000) / 1000]),
    ),
    estimated_cost: Math.round(cost * 10) / 10,
    predicted_quality: quality,
    confidence: confidences[type],
    explanation: explanations[type],
  };
}

/** POST /blend/optimize 的 mock（后端恒 503，必走此分支） */
export function mockOptimize(req: OptimizeRequest): OptimizeResponse {
  const started = Date.now();
  const coals = req.available_coals;
  // 成本优先：越便宜权重越高；质量优先：G 值越高权重越高
  const byCost = distributeByWeight(coals, (c) => 1 / c.price_per_ton);
  const byQuality = distributeByWeight(coals, (c) => Number(c.lab_data.G ?? 0));
  const balanced: Record<string, number> = {};
  for (const c of coals) {
    balanced[c.name] = (byCost[c.name] + byQuality[c.name]) / 2;
  }
  return {
    solutions: [
      estimateSolution(coals, byCost, 'cost_optimal'),
      estimateSolution(coals, byQuality, 'quality_stable'),
      estimateSolution(coals, balanced, 'balanced'),
    ],
    model_version: 'demo-experience-0.1（冷启动经验模型）',
    compute_time_ms: Date.now() - started + 120,
  };
}

/** GET /blend/recipes 的 mock（PG 不可用时降级） */
export function mockRecipes(furnaceId?: number): { recipes: BlendRecipe[] } {
  const rows: BlendRecipe[] = [];
  const base = Date.UTC(2026, 7, 1);
  for (let i = 0; i < 12; i += 1) {
    const furnace = (i % 2) + 1;
    const ai = i % 3 !== 2; // 约 2/3 为 AI 方案
    const estimated = 1280 + ((i * 37) % 120);
    rows.push({
      batch_no: `PB202608${String(14 - i).padStart(2, '0')}-0${furnace}`,
      furnace_id: furnace,
      production_date: new Date(base + (13 - i) * 86400000)
        .toISOString()
        .slice(0, 10),
      total_coal_tons: 950 + ((i * 53) % 200),
      estimated_cost_per_ton: estimated,
      // AI 方案实际成本整体低于人工方案，体现对比意义
      actual_cost_per_ton: estimated + (ai ? ((i * 7) % 15) - 10 : ((i * 11) % 25)),
      ai_generated: ai,
      approved_by: ai ? '王配煤' : null,
    });
  }
  return {
    recipes: furnaceId ? rows.filter((r) => r.furnace_id === furnaceId) : rows,
  };
}

/** POST /blend/feedback 的 mock（仅断网兜底，后端接口本身可用） */
export function mockFeedback(fb: LabFeedback): FeedbackResponse {
  return {
    batch_no: fb.batch_no,
    status: 'accepted',
    detail: '演示模式：已接收（未真正入库），待与预测值比对',
  };
}

/** 质量预测的纯演示实现（后端暂无独立预测接口，TODO：方案§4.1.6 DOE 标定后接通） */
export function mockPredict(req: PredictRequest): PredictResponse {
  const entries = Object.entries(req.ratios).filter(([, r]) => r > 0);
  const coals = presetCoals.filter((c) => (req.ratios[c.name] ?? 0) > 0);
  let gSum = 0;
  let vdafSum = 0;
  for (const c of coals) {
    const r = req.ratios[c.name];
    gSum += r * Number(c.lab_data.G ?? 0);
    vdafSum += r * Number(c.lab_data.Vdaf ?? 0);
  }
  const gAvg = coals.length ? gSum : 0;
  const vdafAvg = coals.length ? vdafSum : 0;
  return {
    predicted_quality: {
      M25: Math.round((78 + gAvg * 0.14) * 10) / 10,
      M10: Math.round((8.5 - gAvg * 0.02) * 10) / 10,
      CSR: Math.round((48 + gAvg * 0.22 - vdafAvg * 0.1) * 10) / 10,
      CRI: Math.round((18 + vdafAvg * 0.25 - gAvg * 0.05) * 10) / 10,
    },
    // 简化解释：该煤种 G 值与均值之差 × 配比，正贡献表示提高强度
    explanations: entries.map(([name, r]) => {
      const coal = presetCoals.find((c) => c.name === name);
      const g = Number(coal?.lab_data.G ?? 60);
      return { coal: name, impact: Math.round((g - 60) * r * 10) / 10 };
    }),
  };
}
