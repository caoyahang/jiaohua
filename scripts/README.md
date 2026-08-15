# scripts/ —— 脚本目录分类约定

bash 脚本首行 `set -euo pipefail` + 中文注释；破坏性操作（清库、删备份）必须有人工确认开关（总纲 §5）。
部署/备份/重训只走脚本，不在文档里写"手动执行某条命令"作为正式流程。

## 分类（文件超过 8 个时再物理分子目录）

| 分类 | 现有文件 | 说明 |
|---|---|---|
| 部署运维 | `deploy.sh`、`backup.sh` | 上线、备份、恢复；destructive 操作需确认开关 |
| 离线任务 | `model_retrain.sh` | 模型重训等周期性离线动作（由调度或人工触发） |
| 开发工具 | `export_openapi.py`、`check.sh` | export_openapi：导出 FastAPI OpenAPI 到 `frontend/shared/openapi.json`（frontend/AGENTS.md §2.1）；check：评审门禁（pytest+红线grep+契约新鲜度，pre-commit 钩子调用） |
| 一次性脚本 | `one_off/`（按需创建） | 迁移/补数等一次性动作，文件头注明用途与可删除日期 |
