"""数据质量日报统计（方案§3.3 数据治理标准）。

依据《AI焦化厂智能化落地方案 V1.1》§3.3：
- 数据采集覆盖率 ≥ 95%（关键工艺参数 100%）
- 数据在线率 ≥ 99%

对经 ``quality_check`` 处理后的 DataFrame 汇总日报指标（覆盖率/在线率/
范围与突变剔除量/缺失插补量），供 services/scheduler/jobs.py 的每日
数据质量日报任务调用（方案§7 阶段七「常态化运营」）。

口径约定（避免自创口径，与方案§3.3 对齐）：
- 覆盖率（coverage_rate）：测点维度——昨日采集到 ≥1 个有效样本的测点数
  占应采集测点总数比例（关键工艺参数须 100%）。
- 在线率（online_rate）：时间维度——全部测点有效样本总数占期望样本总数
  （测点数 × 每测点理论样本数）的比例。
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# 默认告警阈值（方案§3.3：覆盖率 ≥95%、在线率 ≥99%）
DEFAULT_COVERAGE_THRESHOLD = 0.95
DEFAULT_ONLINE_RATE_THRESHOLD = 0.99

# 标记枚举单一事实来源在 data/pipeline/quality_check.py，此处仅引用
_FLAG_SUFFIX = "__flag"
_FLAG_MISSING = "missing"
_FLAG_RANGE_ERR = "range_err"
_FLAG_SPIKE_ERR = "spike_err"
_FLAG_INTERPOLATED = "interpolated"
_FLAG_REVERSAL_EXCLUDED = "reversal_excluded"
_REVERSAL_FLAG_COL = "reversal_flag"


def _value_columns(df: pd.DataFrame) -> List[str]:
    """返回物理量值列（排除 ``__flag`` 标记列与 reversal_flag）。"""
    return [
        c for c in df.columns
        if not c.endswith(_FLAG_SUFFIX) and c != _REVERSAL_FLAG_COL
    ]


def summarize_quality(
    df: pd.DataFrame,
    expected_samples: int,
    coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD,
    online_rate_threshold: float = DEFAULT_ONLINE_RATE_THRESHOLD,
    critical_tags: Optional[List[str]] = None,
) -> Dict[str, object]:
    """统计昨日各测点数据质量（方案§3.3）。

    Args:
        df: 经 quality_check 处理后的 DataFrame：物理量列 + 对应
            ``<列名>__flag`` 标记列（good/range_err/spike_err/interpolated/
            missing），可选 ``reversal_flag`` 列（good/reversal_excluded）。
        expected_samples: 每个测点昨日理论应采样本数（按采样频率推算，
            如 1s 频率一天 = 86400；缺失样本可能未出现在 df 行中）。
        coverage_threshold: 覆盖率告警阈值（默认 0.95，方案§3.3）。
        online_rate_threshold: 在线率告警阈值（默认 0.99，方案§3.3）。
        critical_tags: 关键工艺参数测点名列表，覆盖率须 100%（方案§3.3）。

    Returns:
        Dict:
        - ``per_tag``: 各测点统计（tag/actual/expected/coverage/
          range_err/spike_err/interpolated/missing）。
        - ``coverage_rate``: 整体覆盖率（有数据测点数 / 测点总数）。
        - ``online_rate``: 整体在线率（有效样本总数 / 期望样本总数）。
        - ``tag_count``: 测点总数。
        - ``reversal_excluded_count``: 换向期剔除样本数（行级）。
        - ``alerts``: 超阈值告警清单（覆盖率/在线率/关键测点）。
    """
    if expected_samples <= 0:
        raise ValueError("expected_samples 必须为正整数")

    value_cols = _value_columns(df)
    if not value_cols:
        return {
            "per_tag": [],
            "coverage_rate": 0.0,
            "online_rate": 0.0,
            "tag_count": 0,
            "reversal_excluded_count": 0,
            "alerts": ["无物理量值列，无法统计"],
        }

    per_tag: List[Dict[str, object]] = []
    covered_tags = 0
    total_effective = 0

    for col in value_cols:
        flag_col = f"{col}{_FLAG_SUFFIX}"
        flags = (
            df[flag_col]
            if flag_col in df.columns
            else pd.Series(["good"] * len(df), index=df.index)
        )
        # 有效样本 = 值非 NaN（range_err 已置 NaN，missing 为 NaN）
        actual = int(df[col].notna().sum())
        total_effective += actual
        if actual > 0:
            covered_tags += 1

        per_tag.append({
            "tag": col,
            "actual": actual,
            "expected": expected_samples,
            "coverage": round(actual / expected_samples, 6),
            "range_err": int((flags == _FLAG_RANGE_ERR).sum()),
            "spike_err": int((flags == _FLAG_SPIKE_ERR).sum()),
            "interpolated": int((flags == _FLAG_INTERPOLATED).sum()),
            "missing": int((flags == _FLAG_MISSING).sum()),
        })

    tag_count = len(value_cols)
    total_expected = expected_samples * tag_count
    coverage_rate = covered_tags / tag_count
    online_rate = total_effective / total_expected

    reversal_excluded_count = int(
        (df[_REVERSAL_FLAG_COL] == _FLAG_REVERSAL_EXCLUDED).sum()
        if _REVERSAL_FLAG_COL in df.columns else 0
    )

    alerts: List[str] = []
    if coverage_rate < coverage_threshold:
        alerts.append(
            f"覆盖率 {coverage_rate:.1%} 低于阈值 {coverage_threshold:.0%}"
        )
    if online_rate < online_rate_threshold:
        alerts.append(
            f"在线率 {online_rate:.1%} 低于阈值 {online_rate_threshold:.0%}"
        )
    for tag in (critical_tags or []):
        row = next((t for t in per_tag if t["tag"] == tag), None)
        if row is not None and float(row["coverage"]) < 1.0:
            alerts.append(
                f"关键测点 {tag} 覆盖率 {float(row['coverage']):.1%} < 100%"
            )

    logger.info(
        "数据质量日报: 测点=%d 覆盖率=%.1%% 在线率=%.1%% 告警=%d",
        tag_count, coverage_rate * 100, online_rate * 100, len(alerts),
    )
    return {
        "per_tag": per_tag,
        "coverage_rate": round(coverage_rate, 6),
        "online_rate": round(online_rate, 6),
        "tag_count": tag_count,
        "reversal_excluded_count": reversal_excluded_count,
        "alerts": alerts,
    }
