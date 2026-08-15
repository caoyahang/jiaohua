#!/usr/bin/env bash
# =============================================================================
# backup.sh - 数据备份脚本（PostgreSQL pg_dump + TDengine占位）
#
# 用法: ./scripts/backup.sh [备份目录]     默认 ./backups/YYYYMMDD_HHMMSS
# 说明: 冷数据保留10年（3.3节），备份介质与异地容灾策略由运维另行制定
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

BACKUP_ROOT="${1:-./backups/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "${BACKUP_ROOT}"

echo "===== 数据备份 -> ${BACKUP_ROOT} ====="

# 1. PostgreSQL 全库备份（自定义格式，支持pg_restore按表恢复）
echo "----- 备份 PostgreSQL (coke_plant) -----"
docker compose exec -T postgres \
    pg_dump -U ai_admin -d coke_plant --format=custom --no-owner \
    > "${BACKUP_ROOT}/coke_plant_pg.dump"
echo "PostgreSQL 备份完成: $(du -h "${BACKUP_ROOT}/coke_plant_pg.dump" | cut -f1)"

# 2. TDengine 备份（占位：taosdump在容器内执行，输出到挂载卷）
# TODO: TDengine 3.x 官方备份方式（taosdump 或企业版快照），待数据底座上线后接通
echo "----- 备份 TDengine (占位) -----"
cat > "${BACKUP_ROOT}/TDengine_BACKUP_TODO.txt" <<'EOF'
TDengine备份占位说明：
  方案一: docker compose exec tdengine taosdump -o /var/lib/taos/backup <dbname>
          （需先将备份目录挂载出容器）
  方案二: 直接打包 /var/lib/taos 数据目录（需先停写或打快照）
  热数据7天/温数据6个月的保存周期由TDengine KEEP参数控制，
  冷数据10年需归档到对象存储/磁带。
EOF
echo "TDengine 备份占位文件已生成（见 TDengine_BACKUP_TODO.txt）"

# 3. 备份清单与校验
echo "----- 生成校验清单 -----"
( cd "${BACKUP_ROOT}" && sha256sum * > SHA256SUMS.txt )
echo "===== 备份完成: ${BACKUP_ROOT} ====="

# 4. 清理30天前的旧备份（保留策略按需调整）
find ./backups -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
