# 数据库迁移机制（PostgreSQL）

> 轻量约定：编号增量 SQL + 追踪表，**不引入 Alembic**（方案§6.1 之外的新依赖，且不支持 TDengine）。
> 适用范围：`data/schemas/postgresql.sql` 管理的业务表；TDengine 超级表不走此机制（`tdengine.sql` 维持幂等全量执行）。

## 规则

1. `../postgresql.sql` 保持**全量快照 SSOT**：新环境部署只跑快照即可得到最新结构。
2. **改表 = 两件事一起做**（总纲 §0.3）：
   - 改 `../postgresql.sql` 快照；
   - 新增增量文件 `VNNN__描述.sql`（NNN 从 002 起递增，001 为基线）。
3. 增量文件必须**幂等**（`IF NOT EXISTS` / `IF EXISTS`），允许重复执行不出错。
4. 部署由 `scripts/deploy.sh` 驱动：先跑快照，再按编号顺序执行 `schema_migrations` 表中未记录的增量，每执行成功一个写入一行 `(version, applied_at)`。
5. 已在生产执行过的 V 文件**禁止修改**——错了就再写一个修正版本（V 文件是历史，快照才是现状）。

## 文件命名

```
V001__baseline.sql          # 基线：建 schema_migrations 追踪表
V002__add_xxx_column.sql    # 示例：后续变更
```
