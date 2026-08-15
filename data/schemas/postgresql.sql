-- ============================================================
-- AI焦化厂智能化平台 - PostgreSQL 业务库建表脚本
-- 依据：《AI焦化厂智能化落地方案 V1.1》3.4.1 / 3.4.2 / 3.4.4
-- 建表语句照抄文档（含V1.1新增字段），文末补充索引
-- ============================================================

-- ------------------------------------------------------------
-- 3.4.1 配煤方案表
-- ------------------------------------------------------------
CREATE TABLE blend_recipe (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(50) UNIQUE NOT NULL,    -- 批次号
    furnace_id INT NOT NULL,                  -- 焦炉编号
    production_date DATE NOT NULL,            -- 生产日期
    total_coal_tons DECIMAL(10,2),            -- 总用煤量(吨)
    estimated_cost_per_ton DECIMAL(8,2),      -- 预估吨煤成本(元)
    actual_cost_per_ton DECIMAL(8,2),         -- 实际吨煤成本(元)
    ai_generated BOOLEAN DEFAULT FALSE,       -- 是否AI生成
    operator_id INT,                          -- 操作工ID
    approved_by INT,                          -- 审核人ID
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

-- 配煤明细表
CREATE TABLE blend_detail (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(50) REFERENCES blend_recipe(batch_no),
    coal_type_id INT,                         -- 煤种ID
    coal_name VARCHAR(100),                   -- 煤种名称
    ratio DECIMAL(5,4),                       -- 配比(0~1)
    tonnage DECIMAL(10,2),                    -- 实际用量(吨)
    unit_price DECIMAL(8,2),                  -- 采购单价(元/吨)
    -- 该批次煤的化验指标
    ash DECIMAL(6,2),                         -- 灰分 Ad(%)
    volatile DECIMAL(6,2),                    -- 挥发分 Vdaf(%)
    sulfur DECIMAL(6,3),                      -- 硫分 St,d(%)
    g_value INT,                              -- 粘结指数 G
    y_value DECIMAL(5,2),                     -- 胶质层厚度 Y(mm)
    rmax DECIMAL(5,3),                        -- 镜质组平均最大反射率
    rmax_distribution JSONB,                  -- 镜质组反射率分布直方图(分段占比,如{"0.6-0.7":0.05,...}) V1.1新增
    active_inert_ratio DECIMAL(6,3),          -- 活惰比(活性物/惰性物,煤岩定量) V1.1新增
    csr DECIMAL(5,2),                         -- 单种煤CSR
    cri DECIMAL(5,2)                          -- 单种煤CRI
);

-- ------------------------------------------------------------
-- 3.4.2 焦炭质量化验表（含V1.1新增炼焦工艺参数字段）
-- ------------------------------------------------------------
CREATE TABLE coke_quality (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(50) REFERENCES blend_recipe(batch_no),
    furnace_id INT NOT NULL,
    push_date DATE NOT NULL,                   -- 推焦日期
    -- 冷态强度
    m25 DECIMAL(5,2),                         -- M25(%)
    m10 DECIMAL(5,2),                         -- M10(%)
    -- 热态强度
    csr DECIMAL(5,2),                         -- CSR(%)
    cri DECIMAL(5,2),                         -- CRI(%)
    -- 炼焦工艺参数（V1.1新增：CSR/CRI强依赖工艺侧，缺失会把工艺波动学成噪声）
    coking_time_hours DECIMAL(5,2),           -- 实际结焦时间(h)
    avg_temp_machine DECIMAL(6,1),            -- 机侧平均火道温度(℃)
    avg_temp_coke DECIMAL(6,1),               -- 焦侧平均火道温度(℃)
    bulk_density DECIMAL(5,3),                -- 装炉堆密度实测值(t/m³)
    quenching_mode VARCHAR(10),               -- 'cdq'(干熄) / 'wet'(湿熄)
    cdq_ratio DECIMAL(4,3),                   -- 干熄率(0~1)
    -- 工业分析
    ash DECIMAL(6,2),                         -- 灰分(%)
    volatile DECIMAL(6,2),                    -- 挥发分(%)
    sulfur DECIMAL(6,3),                      -- 硫分(%)
    -- 预测值（AI回填）
    pred_m25 DECIMAL(5,2),
    pred_m10 DECIMAL(5,2),
    pred_csr DECIMAL(5,2),
    pred_cri DECIMAL(5,2),
    pred_error_m25 DECIMAL(5,2),              -- 预测误差
    pred_error_csr DECIMAL(5,2),
    model_version VARCHAR(20),                 -- 模型版本
    lab_operator VARCHAR(50),
    tested_at TIMESTAMP
);

-- ------------------------------------------------------------
-- 3.4.4 设备状态表
-- ------------------------------------------------------------
CREATE TABLE equipment_status (
    id BIGSERIAL PRIMARY KEY,
    equipment_id INT,
    equipment_name VARCHAR(100),     -- 推焦车/拦焦车/风机/泵
    workshop VARCHAR(50),           -- 所属车间
    status VARCHAR(20),             -- running/stopped/maintenance/fault
    -- 监测参数
    motor_current FLOAT,            -- 电机电流(A)
    bearing_temp FLOAT,             -- 轴承温度(℃)
    vibration_speed FLOAT,          -- 振动速度(mm/s)
    vibration_freq JSONB,           -- 振动频谱数据
    oil_temp FLOAT,                 -- 油温
    -- 预测性维护
    health_score DECIMAL(5,2),      -- 设备健康评分(0~100)
    predicted_rul_days INT,         -- 预测剩余寿命(天)
    fault_probability DECIMAL(5,4), -- 故障概率
    last_maintenance_date DATE,
    next_maintenance_date DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 索引（文档之外补充，按查询场景）
-- ============================================================

-- 配煤方案：按生产日期/焦炉查批次，AI回填与驾驶舱报表常用
CREATE INDEX idx_blend_recipe_production_date ON blend_recipe (production_date);
CREATE INDEX idx_blend_recipe_furnace_date ON blend_recipe (furnace_id, production_date);
CREATE INDEX idx_blend_recipe_created_at ON blend_recipe (created_at);

-- 配煤明细：按批次查明细（特征组装主路径）；rmax_distribution 供煤岩分布查询
CREATE INDEX idx_blend_detail_batch_no ON blend_detail (batch_no);
CREATE INDEX idx_blend_detail_coal_type ON blend_detail (coal_type_id);
CREATE INDEX idx_blend_detail_rmax_dist ON blend_detail USING GIN (rmax_distribution);

-- 焦炭质量：按批次/推焦日期回查化验结果（增量学习闭环主路径，见4.1.7）
CREATE INDEX idx_coke_quality_batch_no ON coke_quality (batch_no);
CREATE INDEX idx_coke_quality_push_date ON coke_quality (push_date);
CREATE INDEX idx_coke_quality_furnace_push ON coke_quality (furnace_id, push_date);
CREATE INDEX idx_coke_quality_model_version ON coke_quality (model_version);

-- 设备状态：按设备回查最新状态与检修计划
CREATE INDEX idx_equipment_status_equipment ON equipment_status (equipment_id, updated_at);
CREATE INDEX idx_equipment_status_workshop ON equipment_status (workshop);
CREATE INDEX idx_equipment_status_status ON equipment_status (status);
CREATE INDEX idx_equipment_status_vibration_freq ON equipment_status USING GIN (vibration_freq);
