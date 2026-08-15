#!/usr/bin/env bash
# =============================================================================
# deploy.sh - AI焦化厂智能化平台一键部署脚本
#
# 用法: ./scripts/deploy.sh [环境]     环境默认 production
# 前置: 已安装 docker / docker compose v2，且 .env 已从 .env.example 拷贝并填好密码
# =============================================================================
set -euo pipefail

ENV="${1:-production}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "===== AI焦化厂智能化平台部署 (env=${ENV}) ====="

# 1. 检查环境变量文件
if [[ ! -f .env ]]; then
    echo "[错误] 缺少 .env，请先: cp .env.example .env 并修改密码" >&2
    exit 1
fi

# 2. 检查明文默认密码是否已修改（内网也不允许用change_me上线）
if grep -q "change_me" .env; then
    echo "[错误] .env 中仍存在默认密码 change_me，请先修改" >&2
    exit 1
fi

# 3. 拉取基础镜像 + 构建自研服务镜像
echo "----- 构建镜像 -----"
docker compose build api scheduler

# 4. 启动数据底座（先起库，等健康后再起应用）
echo "----- 启动数据底座 -----"
docker compose up -d tdengine postgres redis
echo "等待 PostgreSQL 就绪..."
until docker compose exec -T postgres pg_isready -U ai_admin -d coke_plant > /dev/null 2>&1; do
    sleep 2
done

# 5. 初始化数据库表结构 + 执行增量迁移（机制见 data/schemas/migrations/README.md）
if [[ -f data/schemas/postgresql.sql ]]; then
    echo "----- 初始化PostgreSQL表结构（幂等快照） -----"
    docker compose exec -T postgres psql -U ai_admin -d coke_plant -f - < data/schemas/postgresql.sql
fi

echo "----- 执行增量迁移 -----"
# 基线：确保追踪表存在
docker compose exec -T postgres psql -U ai_admin -d coke_plant -f - < data/schemas/migrations/V001__baseline.sql
# 按编号顺序执行未应用的 V 文件并记录
for f in $(ls data/schemas/migrations/V*.sql | sort); do
    fname="$(basename "${f}")"
    version="${fname%%__*}"
    desc="${fname#*__}"; desc="${desc%.sql}"
    applied=$(docker compose exec -T postgres psql -U ai_admin -d coke_plant -tA \
        -c "SELECT 1 FROM schema_migrations WHERE version='${version}'" || true)
    if [[ "${applied}" == "1" ]]; then
        echo "  [跳过] ${fname}（已应用）"
        continue
    fi
    echo "  [应用] ${fname}"
    docker compose exec -T postgres psql -U ai_admin -d coke_plant -v ON_ERROR_STOP=1 -f - < "${f}"
    docker compose exec -T postgres psql -U ai_admin -d coke_plant -c \
        "INSERT INTO schema_migrations(version, description) VALUES ('${version}', '${desc}') ON CONFLICT DO NOTHING"
done
# TODO: TDengine建库建表（data/schemas/tdengine.sql，taos CLI执行）

# 6. 启动应用服务
echo "----- 启动应用服务 -----"
docker compose up -d api scheduler

# 7. 健康检查
echo "----- 健康检查 -----"
sleep 5
if curl -fsS http://localhost:8000/health | grep -q '"status"'; then
    echo "===== 部署完成，API健康检查通过 ====="
else
    echo "[警告] API健康检查未通过，请执行: docker compose logs api" >&2
    exit 1
fi
