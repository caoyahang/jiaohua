-- V002 表结构补齐（方案V1.1修订12，3.4.5~3.4.8）：
-- coal 煤种主数据 / pdm_alarm 设备PdM告警 / vision_alarm 视觉告警 / operation_audit 操作审计。
-- 幂等：可重复执行。快照（../postgresql.sql）已同步，本文件供存量库增量升级。

CREATE TABLE IF NOT EXISTS coal (
    id BIGSERIAL PRIMARY KEY,
    coal_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(20),
    supplier VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE,
    ash DECIMAL(6,2),
    volatile DECIMAL(6,2),
    sulfur DECIMAL(6,3),
    g_value INT,
    y_value DECIMAL(5,2),
    rmax DECIMAL(5,3),
    rmax_distribution JSONB,
    active_ratio DECIMAL(5,2),
    inert_ratio DECIMAL(5,2),
    csr DECIMAL(5,2),
    cri DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS pdm_alarm (
    id BIGSERIAL PRIMARY KEY,
    equipment_id INT NOT NULL,
    level VARCHAR(10) NOT NULL,
    source VARCHAR(30),
    metric VARCHAR(50),
    metric_value FLOAT,
    threshold FLOAT,
    iso10816_zone VARCHAR(5),
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    handler VARCHAR(50),
    ack_comment TEXT,
    acked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vision_alarm (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL,
    scene VARCHAR(30) NOT NULL,
    area VARCHAR(50),
    label VARCHAR(50),
    confidence DECIMAL(5,4),
    level VARCHAR(10),
    message TEXT,
    snapshot_url VARCHAR(255),
    acknowledged BOOLEAN DEFAULT FALSE,
    handler VARCHAR(50),
    ack_comment TEXT,
    is_false_positive BOOLEAN DEFAULT FALSE,
    acked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS operation_audit (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50),
    method VARCHAR(10),
    path VARCHAR(255),
    client_ip VARCHAR(45),
    status_code INT,
    elapsed_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coal_category ON coal (category);
CREATE INDEX IF NOT EXISTS idx_coal_enabled ON coal (enabled);
CREATE INDEX IF NOT EXISTS idx_pdm_alarm_equipment ON pdm_alarm (equipment_id, created_at);
CREATE INDEX IF NOT EXISTS idx_pdm_alarm_level ON pdm_alarm (level, acknowledged);
CREATE INDEX IF NOT EXISTS idx_vision_alarm_scene ON vision_alarm (scene, created_at);
CREATE INDEX IF NOT EXISTS idx_vision_alarm_ack ON vision_alarm (acknowledged);
CREATE INDEX IF NOT EXISTS idx_operation_audit_created ON operation_audit (created_at);
CREATE INDEX IF NOT EXISTS idx_operation_audit_user ON operation_audit (username);
