"""现场采集 Worker 入口（方案§3.2/§3.3/§4.2.6）。

当前质量标记持久化链路尚未接通，因此明确拒绝启动，避免采集数据被静默
丢弃或绕过换向期标记。完成 ``TimeSeriesEtl.write_tdengine`` 与断线补采后，
本入口再负责装配 OPC UA、ETL 与 TDengine。
"""

from __future__ import annotations


def main() -> None:
    """拒绝启动未完成的数据链路，避免产生不可追溯数据。"""
    raise NotImplementedError(
        "采集 Worker 尚未接通质量标记持久化与断线补采；禁止用于现场采集"
    )


if __name__ == "__main__":
    main()
