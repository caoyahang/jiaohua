-- ============================================================
-- AI焦化厂智能化平台 - TDengine 时序库建表脚本
-- 依据：《AI焦化厂智能化落地方案 V1.1》3.4.3（照抄）+ 补充 vibration 超级表
-- 使用前提：先执行  CREATE DATABASE coke_plant_ts;  USE coke_plant_ts;
-- ============================================================

-- ------------------------------------------------------------
-- 3.4.3 炉温记录表（超级表，照抄文档）
-- ------------------------------------------------------------
CREATE STABLE furnace_temp (
    ts TIMESTAMP,
    furnace_id INT,
    burner_side VARCHAR(10),          -- 'machine' or 'coke'
    fire_channel_temp FLOAT,         -- 火道温度(℃)
    gas_flow FLOAT,                  -- 煤气流量(m³/h)
    flue_suction FLOAT,              -- 分烟道吸力(Pa)
    collector_pressure FLOAT,        -- 集气管压力(Pa)
    oxygen_content FLOAT,            -- 烟气残氧(%)
    ammonia_flow FLOAT,              -- 氨水流量
    coal_gas_calorific FLOAT,        -- 煤气热值(kJ/m³)
    ai_setpoint_gas FLOAT,           -- AI推荐的煤气流量设定值
    ai_setpoint_suction FLOAT,       -- AI推荐的吸力设定值
    control_mode VARCHAR(10)         -- 'manual' / 'ai_shadow' / 'ai_auto'
) TAGS (
    furnace_name VARCHAR(50),
    capacity INT,                    -- 焦炉产能(万吨/年)
    oven_type VARCHAR(20)            -- 'top_charge' / 'stamp'
);

-- 子表示例（每座焦炉机/焦侧各一张，建表时按实际炉号创建）：
-- CREATE TABLE furnace1_machine USING furnace_temp TAGS ('1#焦炉', 100, 'top_charge');
-- CREATE TABLE furnace1_coke    USING furnace_temp TAGS ('1#焦炉', 100, 'top_charge');

-- ------------------------------------------------------------
-- 补充：设备振动时序超级表（PdM 用，监测参数对齐 3.2.1 Modbus 采集点）
-- 文档未给出该表，由数据底座按 4.3 预测性维护需求补充；
-- TAGS 含设备名/车间/优先级（优先级对齐 4.3.1 的 P0/P1/P2）
-- ------------------------------------------------------------
CREATE STABLE vibration (
    ts TIMESTAMP,
    equipment_id INT,               -- 设备ID（对应 equipment_status.equipment_id）
    vibration_speed FLOAT,          -- 振动速度(mm/s)
    bearing_temp FLOAT,             -- 轴承温度(℃)
    motor_current FLOAT             -- 电机电流(A)
) TAGS (
    equipment_name VARCHAR(100),    -- 设备名（推焦车/拦焦车/风机/泵）
    workshop VARCHAR(50),           -- 所属车间
    priority VARCHAR(4)             -- 监控优先级 'P0' / 'P1' / 'P2'
);

-- 子表示例（每台被监测设备一张）：
-- CREATE TABLE vibration_eq101 USING vibration TAGS ('1#推焦车走行电机', '焦炉', 'P0');
-- CREATE TABLE vibration_eq201 USING vibration TAGS ('煤气鼓风机', '化产', 'P1');
