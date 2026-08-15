"""OPC UA 异步采集客户端（asyncua）。

依据《AI焦化厂智能化落地方案 V1.1》：
- 3.2.1：DCS/PLC 走 OPC UA（强制协议），工艺参数 ≤30s 采集
- 3.2.2：opc.tcp / SignAndEncrypt / Username-Password 或证书认证 / 支持历史读取
- 点位字典来自 config/dcs_tags.yaml 的 opc_ua_server.node_address_space

骨架说明：连接、订阅、回调转发为可运行骨架；TDengine 写入与断线重连
细节以 TODO 标记，待对接实际 DCS 地址空间后补全。
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
    tag_key: Optional[str] = None  # 业务键，如 reversal_status（换向事件源）


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
            )
        )
    return points


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
    ) -> None:
        """
        Args:
            endpoint: OPC UA 端点；为 None 时从环境变量 OPC_UA_ENDPOINT 读取。
            tags_yaml: 点位字典文件路径。
            on_sample: 样本回调，通常由 ETL 管道注入。
            reconnect_interval: 断线重连间隔（秒）。
        """
        self.endpoint = endpoint or os.environ.get("OPC_UA_ENDPOINT", "")
        self.points = load_tag_points(tags_yaml)
        self.on_sample = on_sample
        self.reconnect_interval = reconnect_interval
        self._client: Any = None
        self._subscription: Any = None
        self._running = False

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

    async def write_to_tdengine(self, samples: List[Sample]) -> None:
        """TDengine 写入接口（预留）。

        落库目标为 furnace_temp 超级表（见 data/schemas/tdengine.sql）。
        TODO: 用 taospy 建连接池，按子表（每炉每侧）批量 INSERT；
        写库前必须经过 data.pipeline.quality_check 校验与换向期标记。
        """
        raise NotImplementedError("TDengine 写入待对接 taospy 后实现")


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
