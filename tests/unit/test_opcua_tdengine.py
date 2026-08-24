"""OPC UA 采集 → TDengine 写入的单测（方案§3.2.1/§3.4.3，红线见 data/AGENTS.md §4/§5）。

不依赖 asyncua/taospy：点位解析、SQL 组装（纯函数）与写入编排（假连接）分开测。
"""

import asyncio

import pytest

from data.collector.opcua_client import (
    Sample,
    build_tdengine_statements,
    load_range_limits,
    load_tag_points,
    OpcuaCollector,
)

POINTS_YAML = "config/dcs_tags.yaml"
SETTINGS_YAML = "config/settings.yaml"

NODE_TEMP_M = "ns=2;s=Furnace1.Burner.MachineSide.Temp"
NODE_TEMP_C = "ns=2;s=Furnace1.Burner.CokeSide.Temp"
NODE_O2 = "ns=2;s=Furnace1.Flue.Oxygen"
NODE_REVERSAL = "ns=2;s=Furnace1.Reversal.Status"


@pytest.fixture(scope="module")
def points():
    return load_tag_points(POINTS_YAML)


def test_tag_points_carry_storage_mapping(points):
    """dcs_tags.yaml 的每个工艺点位都必须带 tag_key + furnace_id + burner_side。"""
    by_node = {p.node_id: p for p in points}
    assert by_node[NODE_TEMP_M].tag_key == "fire_channel_temp"
    assert (by_node[NODE_TEMP_M].furnace_id, by_node[NODE_TEMP_M].burner_side) == (1, "machine")
    assert (by_node[NODE_TEMP_C].furnace_id, by_node[NODE_TEMP_C].burner_side) == (1, "coke")
    # 炉级公共量（残氧/氨水/热值）归 common 子表
    assert by_node[NODE_O2].burner_side == "common"
    # 换向事件点位不落 furnace_temp
    assert by_node[NODE_REVERSAL].tag_key == "reversal_status"


def test_build_statements_groups_by_subtable_and_column(points):
    ts = 1755312000.0  # 固定 epoch 秒
    samples = [
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=1234.5, source_ts=ts),
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=1235.0, source_ts=ts + 1),
        Sample(node_id=NODE_TEMP_C, tag_key="fire_channel_temp", value=1230.1, source_ts=ts),
        Sample(node_id=NODE_O2, tag_key="oxygen_content", value=6.5, source_ts=ts),
    ]
    stmts = build_tdengine_statements(samples, points)
    assert len(stmts) == 3  # 机侧温度 / 焦侧温度 / 公共残氧 各一条批量语句

    machine = next(s for s in stmts if s.startswith("INSERT INTO furnace1_machine"))
    assert "(ts, fire_channel_temp)" in machine
    # 同列两点攒成一条 VALUES 列表；时间戳为 epoch 毫秒整数
    assert f"({int(ts * 1000)}, 1234.5)" in machine
    assert f"({int((ts + 1) * 1000)}, 1235.0)" in machine

    assert any(s.startswith("INSERT INTO furnace1_coke") for s in stmts)
    o2 = next(s for s in stmts if s.startswith("INSERT INTO furnace1_common"))
    assert "(ts, oxygen_content)" in o2


def test_reversal_event_not_written(points):
    """红线：换向事件点位是换向期标记的事件源，不入 furnace_temp。"""
    samples = [Sample(node_id=NODE_REVERSAL, tag_key="reversal_status", value=1, source_ts=1.0)]
    assert build_tdengine_statements(samples, points) == []


def test_range_check_blocks_out_of_range(points):
    """范围检查（settings.yaml quality_check.range）：越限样本拦截，正常样本放行。"""
    ranges = load_range_limits(SETTINGS_YAML)
    assert ranges["fire_channel_temp"] == (900.0, 1400.0)
    samples = [
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=1500.0, source_ts=1.0),  # 越上限
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=800.0, source_ts=2.0),   # 越下限
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=1250.0, source_ts=3.0),  # 正常
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value="bad", source_ts=4.0),   # 非数值
    ]
    stmts = build_tdengine_statements(samples, points, ranges)
    assert len(stmts) == 1
    assert "1250.0" in stmts[0]
    assert "1500.0" not in stmts[0] and "800.0" not in stmts[0]


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql):
        self.conn.executed.append(sql)

    def close(self):
        pass


class _FakeTdConn:
    def __init__(self):
        self.executed = []

    def cursor(self):
        return _FakeCursor(self)


def test_write_to_tdengine_executes_statements(points):
    """写入编排：注入假连接，逐条执行组装好的 INSERT，返回执行条数。"""
    collector = OpcuaCollector.__new__(OpcuaCollector)  # 绕过 __init__（不连 OPC UA）
    collector.points = points
    collector._ranges = {"fire_channel_temp": (900.0, 1400.0)}
    collector._td_conn = None

    conn = _FakeTdConn()
    samples = [
        Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=1234.5, source_ts=100.0),
        Sample(node_id=NODE_O2, tag_key="oxygen_content", value=6.5, source_ts=100.0),
    ]
    n = asyncio.run(collector.write_to_tdengine(samples, conn=conn))
    assert n == 2
    assert len(conn.executed) == 2
    assert any("furnace1_machine" in s for s in conn.executed)
    assert any("furnace1_common" in s for s in conn.executed)


def test_write_to_tdengine_empty_when_all_filtered(points):
    collector = OpcuaCollector.__new__(OpcuaCollector)
    collector.points = points
    collector._ranges = {"fire_channel_temp": (900.0, 1400.0)}
    collector._td_conn = None

    conn = _FakeTdConn()
    samples = [Sample(node_id=NODE_TEMP_M, tag_key="fire_channel_temp", value=2000.0, source_ts=1.0)]
    n = asyncio.run(collector.write_to_tdengine(samples, conn=conn))
    assert n == 0
    assert conn.executed == []
