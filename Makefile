# AI焦化厂智能化平台 - 快捷命令
# 使用：make up / make down / make init-db / make test

.PHONY: up down init-db test check check-full logs ps

# 变更后评审门禁（pre-commit 钩子也走这里）
check:
	bash scripts/check.sh

# 完整门禁：追加四个前端工程的 tsc 类型检查
check-full:
	bash scripts/check.sh --full

# 启动全部服务
up:
	docker compose up -d

# 停止全部服务
down:
	docker compose down

# 初始化数据库表结构（PostgreSQL + TDengine）
# 注意：完整部署含增量迁移（data/schemas/migrations/），请优先用 scripts/deploy.sh；
# 本目标仅做快照建表，供开发调试。
init-db:
	docker compose exec -T postgres psql -U ai_admin -d coke_plant -f /schemas/postgresql.sql
	@echo "TODO: 挂载 data/schemas 到容器后执行 tdengine.sql"

# 运行测试
test:
	python -m pytest tests/ -v

# 查看日志
logs:
	docker compose logs -f --tail=100

# 查看服务状态
ps:
	docker compose ps
