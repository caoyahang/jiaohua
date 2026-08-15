/**
 * 接口类型汇总。
 *
 * 红线5：请求/响应类型优先来自 src/api/schema.d.ts（openapi-typescript 生成）。
 * 已知现实（前端规范§2.1）：部分后端路由未声明 response_model，且 pydantic 裸 dict
 * 字段在 schema 中生成为 Record<string, never>（不可用）。这些类型以
 * services/api/routes/blend.py 代码为准在此手写，待后端补 response_model /
 * 为 dict 字段声明具体模型后改从 schema 引入。
 */
import type { components } from './schema';

// ---------- 来自 schema 的类型（后端模型字段完整，可直接用） ----------

export type LoginRequest = components['schemas']['LoginRequest'];
export type TokenResponse = components['schemas']['TokenResponse'];
export type TargetQuality = components['schemas']['TargetQuality'];

// ---------- 手写类型（schema 中裸 dict 不可用，待后端补模型后改从 schema 引入） ----------

/** 煤种化验指标（blend.py CoalInfo.lab_data 的约定字段） */
export interface LabData {
  /** 灰分 % */
  Ad: number;
  /** 挥发分 % */
  Vdaf: number;
  /** 全硫 % */
  St_d: number;
  /** 粘结指数 */
  G: number;
  /** 胶质层厚度 mm */
  Y: number;
  /** 镜质组最大反射率 % */
  Rmax: number;
}

/** 可用煤种信息（对应 blend.py CoalInfo；schema 中 lab_data 为裸 dict 不可直接用） */
export interface CoalInfo {
  coal_id: number;
  name: string;
  stock_tons: number;
  price_per_ton: number;
  /** 配比下限（0~1，工艺约束） */
  min_ratio: number;
  /** 配比上限（0~1，工艺约束） */
  max_ratio: number;
  lab_data: LabData;
}

/** POST /blend/optimize 请求体（对应 blend.py OptimizeRequest） */
export interface OptimizeRequest {
  target_quality: TargetQuality;
  available_coals: CoalInfo[];
  max_cost_per_ton: number;
  priority: 'cost' | 'quality' | 'balanced';
}

/** 焦炭质量四指标（方案§4.1.5） */
export interface QualityMetrics {
  /** 抗碎强度 % */
  M25: number;
  /** 耐磨强度 % */
  M10: number;
  /** 反应后强度 % */
  CSR: number;
  /** 反应性 % */
  CRI: number;
}

/** POST /blend/feedback 请求体（对应 blend.py LabFeedback） */
export interface LabFeedback {
  batch_no: string;
  actual_quality: QualityMetrics;
}

export type SolutionType = 'cost_optimal' | 'quality_stable' | 'balanced';

/** 单套配煤方案（POST /blend/optimize 响应元素） */
export interface BlendSolution {
  type: SolutionType;
  /** 煤名 → 配比（0~1，合计=1） */
  blend_ratio: Record<string, number>;
  /** 预估成本 元/吨 */
  estimated_cost: number;
  predicted_quality: QualityMetrics;
  /** 置信度 0~1（冷启动期为经验值） */
  confidence: number;
  /** SHAP 中文解释 */
  explanation: string;
}

/** POST /blend/optimize 响应（routes/blend.py，优化器未编排时恒 503） */
export interface OptimizeResponse {
  solutions: BlendSolution[];
  model_version: string;
  compute_time_ms: number;
}

/** 历史配煤方案行（GET /blend/recipes，PostgreSQL blend_recipe 表） */
export interface BlendRecipe {
  batch_no: string;
  furnace_id: number;
  production_date: string;
  total_coal_tons: number;
  estimated_cost_per_ton: number;
  actual_cost_per_ton: number | null;
  ai_generated: boolean;
  approved_by: string | null;
}

export interface RecipesResponse {
  recipes: BlendRecipe[];
}

/** POST /blend/feedback 响应 */
export interface FeedbackResponse {
  batch_no: string;
  status: string;
  detail: string;
}

// ---------- 质量预测（后端暂无独立接口，纯前端演示实现） ----------

export interface PredictRequest {
  /** 煤名 → 配比（0~1，合计=1） */
  ratios: Record<string, number>;
}

export interface PredictResponse {
  predicted_quality: QualityMetrics;
  /** 各煤种对质量的影响解释（演示用简化 SHAP） */
  explanations: { coal: string; impact: number }[];
}
