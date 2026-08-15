"""ETL 管道：抽取 → 质量校验 → 入库。

依据《AI焦化厂智能化落地方案 V1.1》：
- 3.3：入库前自动校验；处理延迟 ≤5 秒（从产生到入库）
- 4.2.6：换向期数据入库前打标记、建模前剔除（V1.1红线）

管道骨架：时序数据（DCS 工艺参数 → TDengine）与设备状态
（Modbus → TDengine vibration 超级表 + PostgreSQL equipment_status）两条通路。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from . import quality_check as qc

logger = logging.getLogger(__name__)


@dataclass
class EtlConfig:
    """ETL 运行参数（从 config/settings.yaml 的 quality_check 段加载）。"""

    ranges: Dict[str, tuple]                 # 范围检查阈值
    max_step: Dict[str, float]               # 突变检查阈值
    max_interp_gap_seconds: int              # 可插值最大缺口
    reversal_before_minutes: int             # 换向期前剔除窗口
    reversal_after_minutes: int              # 换向期后剔除窗口
    reversal_event_tag: str                  # 换向事件点位键

    @classmethod
    def from_yaml(cls, settings_yaml: str | Path = "config/settings.yaml") -> "EtlConfig":
        with open(settings_yaml, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        q = cfg["quality_check"]
        return cls(
            ranges={k: tuple(v) for k, v in q["range"].items()},
            max_step={k: float(v) for k, v in q["spike"]["max_step"].items()},
            max_interp_gap_seconds=int(q["missing"]["max_interp_gap_seconds"]),
            reversal_before_minutes=int(q["reversal_exclusion"]["window_before_minutes"]),
            reversal_after_minutes=int(q["reversal_exclusion"]["window_after_minutes"]),
            reversal_event_tag=q["reversal_exclusion"]["event_tag"],
        )


class TimeSeriesEtl:
    """工艺时序数据 ETL：DCS 点位 → 校验 → TDengine furnace_temp 超级表。

    数据流：collector 回调 → 缓冲成微批 DataFrame → validate() →
    mark_reversal_window() → write_tdengine()。
    """

    def __init__(self, config: Optional[EtlConfig] = None) -> None:
        self.config = config or EtlConfig.from_yaml()
        self._buffer: List[Dict[str, Any]] = []  # 微批缓冲

    def on_sample(self, sample: Any) -> None:
        """采集层回调入口：样本进微批缓冲。

        TODO: 按时间窗（如 5s，对齐 3.3 处理延迟 ≤5 秒）或条数阈值
        触发 flush()；当前为占位实现。
        """
        self._buffer.append(
            {
                "ts": pd.Timestamp(sample.source_ts, unit="s"),
                "tag": sample.tag_key,
                "value": sample.value,
            }
        )

    def flush(self) -> pd.DataFrame:
        """把微批缓冲透视为宽表（ts 索引 × 点位列）并清空缓冲。"""
        if not self._buffer:
            return pd.DataFrame()
        long_df = pd.DataFrame(self._buffer)
        self._buffer.clear()
        wide = long_df.pivot_table(index="ts", columns="tag", values="value")
        wide.index = pd.DatetimeIndex(wide.index)
        return wide.sort_index()

    def validate(self, df: pd.DataFrame, reversal_events: List[pd.Timestamp]) -> pd.DataFrame:
        """质量校验全流程：范围 → 突变 → 换向期标记 → 缺失插值。

        顺序说明：先做硬校验（范围/突变）再做换向标记与插值，
        避免换向期脏数据参与插值污染正常段。

        TODO: 换向事件从 reversal_status 点位的上升沿提取
        （点位定义见 dcs_tags.yaml，窗口 2~3 分钟见 settings.yaml）。
        """
        if df.empty:
            return df
        cols = [c for c in df.columns if c in self.config.ranges]
        out = qc.range_check(df, {c: self.config.ranges[c] for c in cols})
        out = qc.spike_check(out, {c: self.config.max_step[c] for c in cols if c in self.config.max_step})
        out = qc.mark_reversal_window(
            out, reversal_events,
            window_before_minutes=self.config.reversal_before_minutes,
            window_after_minutes=self.config.reversal_after_minutes,
        )
        out = qc.interpolate_missing(
            out, cols, max_gap_seconds=self.config.max_interp_gap_seconds
        )
        return out

    def write_tdengine(self, df: pd.DataFrame) -> int:
        """写入 TDengine furnace_temp 超级表（预留接口）。

        入库数据保留全部质量标记（含 reversal_excluded），建模侧用
        quality_check.filter_for_modeling 剔除。

        TODO: taospy 连接池 + 按子表批量 INSERT；URL 从环境变量
        TDENGINE_URL 读取；失败重试与本地落盘兜底（数据在线率 ≥99%）。

        Returns:
            写入行数（当前恒为0，占位）。
        """
        url = os.environ.get("TDENGINE_URL", "")
        logger.info("TDengine 写入占位: url=%s rows=%d", url, len(df))
        return 0

    def run_once(self, reversal_events: List[pd.Timestamp]) -> int:
        """处理一个微批：透视 → 校验 → 入库，返回写入行数。"""
        wide = self.flush()
        checked = self.validate(wide, reversal_events)
        return self.write_tdengine(checked)


class EquipmentStatusEtl:
    """设备状态 ETL：Modbus 样本 → PostgreSQL equipment_status + TDengine vibration 超级表。

    TODO: PostgreSQL 用 psycopg2 连接池 upsert equipment_status
    （按 equipment_id 覆盖最新状态）；振动时序写 vibration 超级表
    （见 data/schemas/tdengine.sql）。
    """

    def __init__(self, config: Optional[EtlConfig] = None) -> None:
        self.config = config or EtlConfig.from_yaml()

    def on_sample(self, sample: Any) -> None:
        """采集层回调入口（DeviceSample，见 data.collector.modbus_client）。"""
        if not sample.ok:
            logger.warning("设备样本读取失败: %s(%d)", sample.equipment_name, sample.device_id)
        # TODO: 组装写入 equipment_status / vibration 超级表

    def write_postgresql(self, samples: List[Any]) -> int:
        """写入 PostgreSQL（预留接口，URL 从环境变量 DATABASE_URL 读取）。"""
        url = os.environ.get("DATABASE_URL", "")
        logger.info("PostgreSQL 写入占位: url=%s rows=%d", url, len(samples))
        return 0
