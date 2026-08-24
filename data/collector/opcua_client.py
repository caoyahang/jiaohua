"""OPC UA 异步采集客户端（asyncua）。

依据《AI焦化厂智能化落地方案 V1.1》：
- 3.2.1：DCS/PLC 走 OPC UA（强制协议），工艺参数 ≤30s 采集
- 3.2.2：opc.tcp / SignAndEncrypt / Username-Password 或证书认证 / 支持历史读取
- 点位字典来自 config/dcs_tags.yaml 的 opc_ua_server.node_address_space

骨架说明：连接、订阅、回调转发为可运行骨架；TDengine 写入已实现
（build_tdengine_statements 纯函数映射 + write_to_tdengine 批量落库）；
安全策略（SignAndEncrypt/证书）与断线缺口补采以 TODO 标记，待对接实际
DCS 地址空间后补全。
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# asyncua 为运行时依赖（技术栈6.1：asyncua）；骨架允许未安装时导入本模块做静态检查
try:
    from asyncua import Client
except ImportError:  # pragma: no cover
    Client = None  # type: ignore[assignment]


@dataclass
class TagPoint:
    """单个 OPC UA 点位定义（对应 dcs_tags.yaml 的一条 node_address_space 记录）。"""

    node_id: str
    description: str
    data_type: str
    unit: str
    sampling_rate_ms: int
    tag_key: Optional[str] = None     # furnace_temp 列名；事件源为 reversal_status
    furnace_id: Optional[int] = None  # 焦炉编号（落库子表维度）
    burner_side: Optional[str] = None # machine / coke / common（炉级公共量）


@dataclass
class Sample:
    """一条采集样本，交给 ETL 管道统一处理。"""

    node_id: str
    tag_key: str
    value: Any
    source_ts: float  # 源时间戳（秒）
    quality: str = "good"


def load_tag_points(tags_yaml: str | Path) -> List[TagPoint]:
    """从 config/dcs_tags.yaml 加载 OPC UA 点位列表。

    Args:
        tags_yaml: dcs_tags.yaml 文件路径。

    Returns:
        TagPoint 列表；sampling_rate 字符串（如 "1000ms"）解析为毫秒整数。
    """
    with open(tags_yaml, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    points: List[TagPoint] = []
    for item in cfg.get("opc_ua_server", {}).get("node_address_space", []):
        rate = str(item.get("sampling_rate", "30000ms")).lower().replace("ms", "")
        points.append(
            TagPoint(
                node_id=item["node_id"],
                description=item.get("description", ""),
                data_type=item.get("data_type", "Float"),
                unit=item.get("unit", ""),
                sampling_rate_ms=int(rate),
                tag_key=item.get("tag_key"),
                furnace_id=item.get("furnace_id"),
                burner_side=item.get("burner_side"),
            )
        )
    return points


# 事件源点位（换向机构状态）：不入 furnace_temp（无对应列），由 ETL 管道消费做换向期标记
EVENT_TAGS = frozenset({"reversal_status"})


def load_range_limits(settings_yaml: str | Path = "config/settings.yaml") -> Dict[str, tuple]:
    """从 settings.yaml 读取物理范围检查上下限（quality_check.range 段）。"""
    with open(settings_yaml, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return {
        k: (float(v[0]), float(v[1]))
        for k, v in cfg.get("quality_check", {}).get("range", {}).items()
    }


def build_tdengine_statements(
    samples: List[Sample],
    points: List[TagPoint],
    ranges: Optional[Dict[str, tuple]] = None,
) -> List[str]:
    """把采集样本映射为 TDengine 批量 INSERT 语句（纯函数，便于单测）。

    规则：
    - 子表名 = furnace{furnace_id}_{burner_side}（如 furnace1_machine）；
    - 事件源点位（reversal_status）跳过，不写 furnace_temp；
    - 范围检查（settings.yaml quality_check.range）：越限样本**跳过并计数告警**
      ——furnace_temp 无标记列，入库侧只能拦在门外；完整的四道质量校验
      （范围/突变/缺失插值/换向期标记）由 ETL 管道对批量数据执行
      （data/pipeline/quality_check.py，红线见 data/AGENTS.md §5）。

    Returns:
        SQL 语句列表，形如
        ``INSERT INTO furnace1_machine (ts, fire_channel_temp) VALUES (169..., 1234.5), ...;``
    """
    point_by_node = {p.node_id: p for p in points}
    # 按 (子表, 列) 分组攒批
    groups: Dict[tuple, List[tuple]] = {}
    skipped_range = 0
    for s in samples:
        p = point_by_node.get(s.node_id)
        if p is None or p.tag_key is None or p.tag_key in EVENT_TAGS:
            continue
        if p.furnace_id is None or p.burner_side is None:
            logger.warning("点位 %s 缺少 furnace_id/burner_side 落库映射，跳过", p.node_id)
            continue
        if ranges and p.tag_key in ranges:
            lo, hi = ranges[p.tag_key]
            try:
                v = float(s.value)
            except (TypeError, ValueError):
                skipped_range += 1
                continue
            if v < lo or v > hi:
                skipped_range += 1
                continue
        else:
            v = float(s.value)
        subtable = f"furnace{p.furnace_id}_{p.burner_side}"
        ts_ms = int(s.source_ts * 1000)
        groups.setdefault((subtable, p.tag_key), []).append((ts_ms, v))
    if skipped_range:
        logger.warning("范围检查拦截 %d 个越限样本（不入库）", skipped_range)

    statements: List[str] = []
    for (subtable, column), rows in groups.items():
        values = ", ".join(f"({ts}, {val})" for ts, val in rows)
        statements.append(f"INSERT INTO {subtable} (ts, {column}) VALUES {values};")
    return statements


class OpcuaCollector:
    """OPC UA 异步采集客户端。

    职责：连接 DCS 的 OPC UA 服务器 → 订阅 dcs_tags.yaml 中的点位 →
    数据变化回调转成 Sample → 交给下游回调（ETL 管道）。

    安全红线（4.2.6）：本客户端只读采集；任何设定值写回走独立的、
    带 DCS 侧硬钳位的控制通道，不在本类中实现。
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        tags_yaml: str | Path = "config/dcs_tags.yaml",
        on_sample: Optional[Callable[[Sample], None]] = None,
        reconnect_interval: float = 5.0,
        settings_yaml: str | Path = "config/settings.yaml",
    ) -> None:
        """
        Args:
            endpoint: OPC UA 端点；为 None 时从环境变量 OPC_UA_ENDPOINT 读取。
            tags_yaml: 点位字典文件路径。
            on_sample: 样本回调，通常由 ETL 管道注入。
            reconnect_interval: 断线重连间隔（秒）。
            settings_yaml: 全局配置路径（读 quality_check.range 范围检查上下限）。
        """
        self.endpoint = endpoint or os.environ.get("OPC_UA_ENDPOINT", "")
        self.points = load_tag_points(tags_yaml)
        self.on_sample = on_sample
        self.reconnect_interval = reconnect_interval
        self._settings_yaml = settings_yaml
        self._client: Any = None
        self._subscription: Any = None
        self._running = False
        self._td_conn: Any = None
        self._ranges: Optional[Dict[str, tuple]] = None

    async def connect(self) -> None:
        """建立 OPC UA 会话（SignAndEncrypt + 用户名/口令或证书）。

        TODO: 按 3.2.2 接入安全策略：set_security_string / 证书加载 /
        用户名口令从环境变量（OPC_UA_USERNAME / OPC_UA_PASSWORD）读取。
        """
        if Client is None:
            raise RuntimeError("asyncua 未安装，无法建立 OPC UA 连接")
        self._client = Client(url=self.endpoint)
        await self._client.connect()
        logger.info("OPC UA 已连接: %s，点位数=%d", self.endpoint, len(self.points))

    async def subscribe(self) -> None:
        """订阅全部点位，数据变化时触发 ``_on_data_change``。

        TODO: 按点位 sampling_rate_ms 分组创建多个 Subscription，
        避免高频点（1s火温）与低频点（5min热值）共用同一发布周期。
        """
        if self._client is None:
            raise RuntimeError("尚未连接，请先调用 connect()")
        handler = _SubscriptionHandler(self)
        self._subscription = await self._client.create_subscription(
            period=1000, handler=handler
        )
        for point in self.points:
            node = self._client.get_node(point.node_id)
            await self._subscription.subscribe_data_change(node)
        logger.info("OPC UA 订阅完成: %d 个点位", len(self.points))

    async def run_forever(self) -> None:
        """采集主循环：连接 → 订阅 → 常驻；异常时断线重连。

        TODO: 断线重连细化——
        1. 区分网络断链与会话过期（重新激活 vs 重建会话）；
        2. 重连期间数据缺口用 history_read 补采（3.2.2 要求历史读取 30 天）；
        3. 重连退避策略与告警上报（数据在线率 ≥99% 考核，见3.3）。
        """
        self._running = True
        while self._running:
            try:
                await self.connect()
                await self.subscribe()
                while self._running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "OPC UA 连接中断，%.1f 秒后重连", self.reconnect_interval
                )
                await asyncio.sleep(self.reconnect_interval)
            finally:
                await self.disconnect()

    async def disconnect(self) -> None:
        """关闭订阅与会话（幂等，允许在 finally 中重复调用）。"""
        try:
            if self._subscription is not None:
                await self._subscription.delete()
            if self._client is not None:
                await self._client.disconnect()
        except Exception:
            logger.exception("OPC UA 断开连接时出错（已忽略）")
        finally:
            self._subscription = None
            self._client = None

    def stop(self) -> None:
        """请求停止主循环。"""
        self._running = False

    def _on_data_change(self, node_id: str, value: Any, source_ts: float) -> None:
        """订阅回调入口：把原始变化事件转为 Sample 并交给下游。"""
        point = next((p for p in self.points if p.node_id == node_id), None)
        if point is None:
            return
        sample = Sample(
            node_id=node_id,
            tag_key=point.tag_key or point.description,
            value=value,
            source_ts=source_ts,
        )
        if self.on_sample is not None:
            self.on_sample(sample)

    async def write_to_tdengine(self, samples: List[Sample], conn: Any = None) -> int:
        """批量写入 TDengine furnace_temp 超级表（方案§3.4.3）。

        映射规则与质量门槛见 ``build_tdengine_statements``。
        连接：优先用入参 ``conn``（便于测试/连接池注入）；否则按 TDENGINE_URL
        懒建连并缓存，写失败时抛弃缓存连接待下次重建（断线重连，data/AGENTS.md §4）。

        Returns:
            实际执行的 INSERT 语句条数。
        """
        if self._ranges is None:
            self._ranges = load_range_limits(self._settings_yaml)
        statements = build_tdengine_statements(samples, self.points, self._ranges)
        if not statements:
            return 0
        own_conn = conn is None
        if own_conn:
            conn = self._get_td_conn()
        try:
            cur = conn.cursor()
            try:
                for sql in statements:
                    cur.execute(sql)
            finally:
                cur.close()
        except Exception:
            if own_conn:
                self._td_conn = None  # 抛弃可疑连接，下次调用重建
            logger.exception("TDengine 批量写入失败（%d 条语句）", len(statements))
            raise
        logger.info("TDengine 写入完成: %d 条 INSERT", len(statements))
        return len(statements)

    def _get_td_conn(self) -> Any:
        """懒建并缓存 TDengine 连接（taospy 懒加载，未装也能 import 本模块）。"""
        if self._td_conn is None:
            url = os.environ.get("TDENGINE_URL", "")
            if not url:
                raise RuntimeError("TDENGINE_URL 未配置")
            import taospy  # noqa: PLC0415

            self._td_conn = taospy.connect(url=url)
        return self._td_conn


class _SubscriptionHandler:
    """asyncua 订阅回调适配器：把 SDK 事件桥接到 OpcuaCollector。"""

    def __init__(self, collector: "OpcuaCollector") -> None:
        self._collector = collector

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        node_id = node.nodeid.to_string()
        source_ts = 0.0
        try:
            source_ts = data.monitored_item.Value.SourceTimestamp.timestamp()
        except Exception:
            import time

            source_ts = time.time()
        self._collector._on_data_change(node_id, val, source_ts)

    def status_change_notification(self, status: Any) -> None:
        logger.warning("OPC UA 订阅状态变化: %s", status)
