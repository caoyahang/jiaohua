-- V001 基线：schema_migrations 追踪表（迁移机制见本目录 README.md）。
-- 业务表结构的全量快照在 ../postgresql.sql，本文件不重复建表。

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,           -- 如 'V001'
    description TEXT NOT NULL DEFAULT '',   -- 迁移描述
    applied_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
