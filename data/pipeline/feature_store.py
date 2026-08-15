"""配煤特征存储：约40维配煤特征组装与特征分组常量定义。

依据《AI焦化厂智能化落地方案 V1.1》4.1.4 特征工程清单（V1.1修订）：

- 单种煤基础指标（7维）：Ad / Vdaf / St,d / G / Y / Rmax均值 / 活惰比
- 镜质组反射率分布直方图（8~12维）：Rmax 0.5~2.0 分段占比
  ⚠️ V1.1修正：单值Rmax表达不了混配后分布的"凹口"（配煤大忌），必须用分布特征
- 配比特征（5维）：各煤种配比熵、最大单一占比、最低占比、配比方差等
- 成本特征（3维）：吨煤成本、加权单价、近30天价格波动率
- 煤岩组合特征（5维）：活性物/惰性物含量、活惰比、流动性指数(G×Y/Ad)、
  镜质组丰度、壳质组含量
- 工艺特征（4维）：装炉堆密度、水分Mt、粉碎细度、配合煤CSR预估值
- 炼焦工艺特征（5维，V1.1新增）：结焦时间、机/焦侧平均火温、
  堆密度实测、熄焦方式、干熄率——不喂会把工艺波动学成噪声
- 约束特征（4维）：库存可用天数、供应商最低采购量、在途量、合同锁价量

特征列名是配煤模型（LightGBM）与优化器（GA）的统一契约，改动需同步
config/model_config.yaml 与 models/quality_predictor。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 镜质组反射率分布分段（Rmax 0.5~2.0，共10段 → 10维分布特征，在8~12维区间内）
# ---------------------------------------------------------------------------
RMAX_BINS: List[str] = [
    "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0",
    "1.0-1.1", "1.1-1.2", "1.2-1.4", "1.4-1.6", "1.6-2.0",
]

# ---------------------------------------------------------------------------
# 特征分组常量（特征列名契约）
# ---------------------------------------------------------------------------

# 单种煤基础指标（7维，配合煤加权值）
COAL_BASIC_FEATURES: List[str] = [
    "ad",                 # 灰分 Ad(%)
    "vdaf",               # 挥发分 Vdaf(%)
    "st_d",               # 硫分 St,d(%)
    "g_value",            # 粘结指数 G
    "y_value",            # 胶质层厚度 Y(mm)
    "rmax_mean",          # 镜质组平均最大反射率
    "active_inert_ratio", # 活惰比（煤岩定量实测）
]

# 镜质组反射率分布直方图（10维，混配后分布——含"凹口"信息）
RMAX_DIST_FEATURES: List[str] = [f"rmax_dist_{b}" for b in RMAX_BINS]

# 配比特征（5维）
RATIO_FEATURES: List[str] = [
    "ratio_entropy",      # 配比熵（衡量配比分散度）
    "max_single_ratio",   # 最大单一煤种占比
    "min_single_ratio",   # 最低占比煤种
    "ratio_variance",     # 配比方差
    "coal_type_count",    # 参与煤种数
]

# 成本特征（3维）
COST_FEATURES: List[str] = [
    "cost_per_ton",           # 吨煤成本（元）
    "weighted_unit_price",    # 各煤种加权单价（元/吨）
    "price_volatility_30d",   # 近30天价格波动率
]

# 煤岩组合特征（5维，煤岩定量实测，非估算）
PETROGRAPHIC_FEATURES: List[str] = [
    "active_matter",              # 活性物含量(%)
    "inert_matter",               # 惰性物含量(%)
    "active_inert_ratio_petro",   # 活惰比（活性物/惰性物）
    "fluidity_index",             # 流动性指数 G×Y/Ad
    "vitrinite_liptinite_ratio",  # 镜质组丰度 / 壳质组含量（合并一维）
]

# 工艺特征（4维，备煤侧）
PROCESS_FEATURES: List[str] = [
    "bulk_density",       # 装炉煤堆密度(t/m³)
    "moisture_mt",        # 水分 Mt(%)
    "fineness_below_3mm", # 粉碎细度（<3mm占比%）
    "blend_csr_estimate", # 配合煤CSR预估值（经验模型打底）
]

# 炼焦工艺特征（5维，V1.1新增——CSR/CRI强依赖工艺侧）
COKING_PROCESS_FEATURES: List[str] = [
    "coking_time_hours",   # 实际结焦时间(h)
    "avg_temp_machine",    # 机侧平均火道温度(℃)
    "avg_temp_coke",       # 焦侧平均火道温度(℃)
    "quenching_mode",      # 熄焦方式（cdq=1/wet=0，入库前one-hot或数值化）
    "cdq_ratio",           # 干熄率(0~1)
]
# 注：装炉堆密度实测值以 bulk_density（工艺特征组）为准，与 3.4.2 表字段对应。

# 约束特征（4维）
CONSTRAINT_FEATURES: List[str] = [
    "stock_days_min",        # 各煤种库存可用天数（最小值）
    "min_purchase_tons",     # 供应商最低采购量(吨)
    "in_transit_tons",       # 运输在途量(吨)
    "contract_locked_tons",  # 合同锁价量(吨)
]

# 全量特征清单（约40维）：顺序即模型输入列顺序
ALL_FEATURES: List[str] = (
    COAL_BASIC_FEATURES
    + RMAX_DIST_FEATURES
    + RATIO_FEATURES
    + COST_FEATURES
    + PETROGRAPHIC_FEATURES
    + PROCESS_FEATURES
    + COKING_PROCESS_FEATURES
    + CONSTRAINT_FEATURES
)

# 预测目标（对应 coke_quality 表）
TARGETS: List[str] = ["m25", "m10", "csr", "cri"]


def weighted_blend_ratios(blend_detail: pd.DataFrame, value_col: str) -> float:
    """按配比对单种煤指标求加权和。

    Args:
        blend_detail: blend_detail 表记录（含 ratio 列与化验指标列）。
        value_col: 待加权列名（如 "ash"）。

    Returns:
        加权和；配比和为0时返回 NaN。
    """
    ratio_sum = blend_detail["ratio"].sum()
    if ratio_sum <= 0:
        return float("nan")
    return float((blend_detail["ratio"] * blend_detail[value_col]).sum() / ratio_sum)


def mix_rmax_distribution(blend_detail: pd.DataFrame) -> Dict[str, float]:
    """混配镜质组反射率分布：按配比对各单种煤分布直方图加权叠加。

    V1.1修正的核心：混配后的分布可能出现"凹口"（配煤大忌），单值Rmax
    表达不了，必须保留分布特征。输入来自 blend_detail.rmax_distribution
    （JSONB，如 {"0.6-0.7": 0.05, ...}）。

    Args:
        blend_detail: blend_detail 表记录（含 ratio 与 rmax_distribution 列）。

    Returns:
        {rmax_dist_<分段>: 混配占比}，覆盖 RMAX_DIST_FEATURES 全部列；
        缺分布数据的煤种按 rmax 均值落入对应分段（降级处理）。
    """
    mixed = {name: 0.0 for name in RMAX_DIST_FEATURES}
    total_ratio = float(blend_detail["ratio"].sum())
    if total_ratio <= 0:
        return mixed

    for _, row in blend_detail.iterrows():
        w = float(row["ratio"]) / total_ratio
        dist = row.get("rmax_distribution")
        if isinstance(dist, dict) and dist:
            for bin_label, share in dist.items():
                col = f"rmax_dist_{bin_label}"
                if col in mixed:
                    mixed[col] += w * float(share)
        elif pd.notna(row.get("rmax")):
            # 降级：无分布数据时按 Rmax 均值落入对应分段（TODO: 外送煤岩检测补齐）
            rmax = float(row["rmax"])
            for bin_label in RMAX_BINS:
                lo, hi = (float(x) for x in bin_label.split("-"))
                if lo <= rmax < hi:
                    mixed[f"rmax_dist_{bin_label}"] += w
                    break
    return mixed


def build_features(
    blend_detail: pd.DataFrame,
    coking_process: Optional[Dict[str, Any]] = None,
    cost_info: Optional[Dict[str, Any]] = None,
    constraint_info: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """组装一个批次的完整特征向量（单行 DataFrame，列=ALL_FEATURES）。

    Args:
        blend_detail: blend_detail 表记录（配比+单种煤化验指标）。
        coking_process: 炼焦工艺参数（结焦时间/火温/熄焦方式/干熄率），
            来自 coke_quality 表工艺字段或炉温时序聚合。
        cost_info: 成本侧数据（单价、近30天波动率）。
        constraint_info: 约束侧数据（库存/采购/在途/锁价）。

    Returns:
        单行 DataFrame，列顺序 = ALL_FEATURES；缺失信息填 NaN 并记日志，
        由模型侧决定剔除或填充（TODO: 缺失策略与模型训练对齐）。

    TODO: 特征落库——结果写入 PostgreSQL 特征表并缓存到 Redis 热特征
    （见 3.1 Redis 用途），供优化器在线调用。
    """
    feat: Dict[str, float] = {}

    # ---- 单种煤基础指标（配比加权）----
    col_map = {
        "ad": "ash", "vdaf": "volatile", "st_d": "sulfur",
        "g_value": "g_value", "y_value": "y_value",
        "rmax_mean": "rmax", "active_inert_ratio": "active_inert_ratio",
    }
    for feat_name, src_col in col_map.items():
        feat[feat_name] = (
            weighted_blend_ratios(blend_detail, src_col)
            if src_col in blend_detail.columns else float("nan")
        )

    # ---- 反射率分布（10维）----
    feat.update(mix_rmax_distribution(blend_detail))

    # ---- 配比特征（5维）----
    ratios = blend_detail["ratio"].to_numpy(dtype=float)
    ratios = ratios / ratios.sum() if ratios.sum() > 0 else ratios
    nz = ratios[ratios > 0]
    feat["ratio_entropy"] = float(-(nz * np.log(nz)).sum()) if nz.size else 0.0
    feat["max_single_ratio"] = float(ratios.max()) if ratios.size else float("nan")
    feat["min_single_ratio"] = float(nz.min()) if nz.size else float("nan")
    feat["ratio_variance"] = float(ratios.var()) if ratios.size else float("nan")
    feat["coal_type_count"] = float(nz.size)

    # ---- 成本特征（3维）----
    cost_info = cost_info or {}
    if "unit_price" in blend_detail.columns:
        feat["weighted_unit_price"] = weighted_blend_ratios(blend_detail, "unit_price")
    else:
        feat["weighted_unit_price"] = float("nan")
    feat["cost_per_ton"] = float(cost_info.get("cost_per_ton", feat["weighted_unit_price"]))
    feat["price_volatility_30d"] = float(cost_info.get("price_volatility_30d", "nan"))

    # ---- 煤岩组合特征（5维）----
    # TODO: 活性物/惰性物/镜质组丰度/壳质组含量需煤岩定量实测数据
    # （3.4.1 暂未建字段，需 LIMS 对接后补充）；当前由活惰比与经验式推算占位。
    air = feat.get("active_inert_ratio", float("nan"))
    feat["active_matter"] = float("nan")   # TODO: LIMS 煤岩定量
    feat["inert_matter"] = float("nan")    # TODO: LIMS 煤岩定量
    feat["active_inert_ratio_petro"] = air
    ad, g, y = feat.get("ad"), feat.get("g_value"), feat.get("y_value")
    feat["fluidity_index"] = (
        float(g * y / ad) if ad and not np.isnan(ad) and ad > 0 else float("nan")
    )
    feat["vitrinite_liptinite_ratio"] = float("nan")  # TODO: LIMS 煤岩定量

    # ---- 工艺特征（4维，备煤侧）----
    coking = coking_process or {}
    feat["bulk_density"] = float(coking.get("bulk_density", "nan"))
    feat["moisture_mt"] = float(coking.get("moisture_mt", "nan"))
    feat["fineness_below_3mm"] = float(coking.get("fineness_below_3mm", "nan"))
    feat["blend_csr_estimate"] = float(coking.get("blend_csr_estimate", "nan"))

    # ---- 炼焦工艺特征（5维，V1.1新增）----
    feat["coking_time_hours"] = float(coking.get("coking_time_hours", "nan"))
    feat["avg_temp_machine"] = float(coking.get("avg_temp_machine", "nan"))
    feat["avg_temp_coke"] = float(coking.get("avg_temp_coke", "nan"))
    mode = coking.get("quenching_mode")
    feat["quenching_mode"] = 1.0 if mode == "cdq" else (0.0 if mode == "wet" else float("nan"))
    feat["cdq_ratio"] = float(coking.get("cdq_ratio", "nan"))

    # ---- 约束特征（4维）----
    constraint_info = constraint_info or {}
    for name in CONSTRAINT_FEATURES:
        feat[name] = float(constraint_info.get(name, "nan"))

    missing = [c for c in ALL_FEATURES if np.isnan(feat.get(c, np.nan))]
    if missing:
        logger.info("特征缺失 %d/%d 维: %s", len(missing), len(ALL_FEATURES), missing)
    return pd.DataFrame([{c: feat.get(c, np.nan) for c in ALL_FEATURES}])
