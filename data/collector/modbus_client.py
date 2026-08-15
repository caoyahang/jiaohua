"""Modbus TCP 设备状态采集客户端（pymodbus）。

依据《AI焦化厂智能化落地方案 V1.1》：
- 3.2.1：设备状态走 Modbus TCP（电机电流、轴承温度、振动值），≤10s 采集
- 4.3.1：监控对象分优先级（P0 推焦车/拦焦车等）
- 点位字典来自 config/dcs_tags.yaml 的 modbus_devices

采集结果供设备预测性维护（PdM）的孤立森林异常检测使用（4.3.2），
入库目标为 equipment_status 表（PostgreSQL）与 vibration 时序超级表（TDengine）。
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# pymodbus 为运行时依赖（技术栈6.1）；骨架允许未安装时导入本模块做静态检查
try:
    from pymodbus.client import ModbusTcpClient
except ImportError:  # pragma: no cover
    try:
        # pymodbus < 3.x 的旧导入路径
        from pymodbus.client.sync import ModbusTcpClient  # type: ignore[no-redef]
    except ImportError:
        ModbusTcpClient = None  # type: ignore[assignment]


@dataclass
class RegisterDef:
    """单个寄存器点位定义。"""

    address: int
    name: str            # motor_current / bearing_temp / vibration_speed / oil_temp
    description: str
    data_type: str       # Float32
    unit: str
    scale: float = 1.0   # 原始值 × scale = 工程量


@dataclass
class DeviceDef:
    """单台被监测设备定义（对应 dcs_tags.yaml 的 modbus_devices 一条记录）。"""

    device_id: int
    equipment_name: str
    workshop: str
    priority: str                 # P0 / P1 / P2（见4.3.1）
    poll_interval_ms: int = 10000
    registers: List[RegisterDef] = field(default_factory=list)


@dataclass
class DeviceSample:
    """一台设备一轮轮询的采集结果。"""

    device_id: int
    equipment_name: str
    workshop: str
    priority: str
    values: Dict[str, float]      # {寄存器名: 工程量值}
    sample_ts: float              # 采集时间戳（秒）
    ok: bool = True


def load_devices(tags_yaml: str | Path) -> List[DeviceDef]:
    """从 config/dcs_tags.yaml 加载 Modbus 设备点位列表。"""
    with open(tags_yaml, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    devices: List[DeviceDef] = []
    for d in cfg.get("modbus_devices", []):
        registers = [
            RegisterDef(
                address=r["address"],
                name=r["name"],
                description=r.get("description", ""),
                data_type=r.get("data_type", "Float32"),
                unit=r.get("unit", ""),
                scale=float(r.get("scale", 1.0)),
            )
            for r in d.get("registers", [])
        ]
        devices.append(
            DeviceDef(
                device_id=d["device_id"],
                equipment_name=d.get("equipment_name", ""),
                workshop=d.get("workshop", ""),
                priority=d.get("priority", "P2"),
                poll_interval_ms=int(d.get("poll_interval_ms", 10000)),
                registers=registers,
            )
        )
    return devices


class ModbusCollector:
    """Modbus TCP 设备状态采集器（轮询模式）。

    职责：按设备点表周期轮询保持寄存器 → 量程换算 → 组装 DeviceSample →
    交给下游回调（ETL 管道）。
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        tags_yaml: str | Path = "config/dcs_tags.yaml",
        unit_id: int = 1,
        timeout: float = 3.0,
        on_sample: Optional[Callable[[DeviceSample], None]] = None,
    ) -> None:
        """
        Args:
            host: Modbus 网关地址；为 None 时读环境变量 MODBUS_HOST。
            port: 端口；为 None 时读环境变量 MODBUS_PORT（默认502）。
            tags_yaml: 点位字典文件路径。
            unit_id: 从站地址。
            timeout: 单次请求超时（秒）。
            on_sample: 样本回调，通常由 ETL 管道注入。
        """
        self.host = host or os.environ.get("MODBUS_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("MODBUS_PORT", "502"))
        self.unit_id = unit_id
        self.timeout = timeout
        self.devices = load_devices(tags_yaml)
        self.on_sample = on_sample
        self._client: Any = None

    def connect(self) -> None:
        """建立 Modbus TCP 连接。"""
        if ModbusTcpClient is None:
            raise RuntimeError("pymodbus 未安装，无法建立 Modbus 连接")
        self._client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
        if not self._client.connect():
            raise ConnectionError(f"Modbus 连接失败: {self.host}:{self.port}")
        logger.info("Modbus 已连接: %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        """关闭连接（幂等）。"""
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def poll_device(self, device: DeviceDef) -> DeviceSample:
        """轮询单台设备的全部寄存器，返回量程换算后的样本。

        读取失败时返回 ``ok=False`` 的空样本，由质量校验层按缺失处理，
        不在采集层重试阻塞其他设备。

        TODO: Float32 跨两个寄存器的字序（大端/小端/字交换）按现场设备
        点表确认后用 pymodbus BinaryPayloadDecoder 解析；当前按相邻两个
        保持寄存器读出原始值做占位换算。
        """
        values: Dict[str, float] = {}
        ok = True
        for reg in device.registers:
            try:
                result = self._client.read_holding_registers(
                    reg.address, 2, slave=self.unit_id
                )
                if result.isError():
                    raise IOError(f"寄存器读取错误: address={reg.address}")
                raw = result.registers[0]  # TODO: 字序确认后解码 Float32
                values[reg.name] = raw * reg.scale
            except Exception:
                logger.exception(
                    "Modbus 读取失败: device=%s(%d) register=%s",
                    device.equipment_name, device.device_id, reg.name,
                )
                ok = False
        return DeviceSample(
            device_id=device.device_id,
            equipment_name=device.equipment_name,
            workshop=device.workshop,
            priority=device.priority,
            values=values,
            sample_ts=time.time(),
            ok=ok,
        )

    def poll_all(self) -> List[DeviceSample]:
        """轮询全部设备一轮，返回样本列表。"""
        if self._client is None:
            raise RuntimeError("尚未连接，请先调用 connect()")
        samples = [self.poll_device(d) for d in self.devices]
        if self.on_sample is not None:
            for s in samples:
                self.on_sample(s)
        return samples

    def run_forever(self) -> None:
        """轮询主循环（阻塞式，建议由调度层以独立线程/进程托管）。

        TODO: 按设备 poll_interval_ms 分频调度（当前统一按最小间隔轮询）；
        断线自动重连与告警（数据在线率 ≥99% 考核，见3.3）。
        """
        self.connect()
        min_interval = min(d.poll_interval_ms for d in self.devices) / 1000.0
        try:
            while True:
                started = time.time()
                self.poll_all()
                elapsed = time.time() - started
                time.sleep(max(0.0, min_interval - elapsed))
        finally:
            self.disconnect()
