# CLAUDE.md — Claude Code 项目入口

> 本文件是 Claude Code 在本项目工作时的入口。项目规范**唯一来源**是 `AGENTS.md`（总纲）及各目录嵌套的分域 AGENTS.md，本文件不复制规则，只做导入与终端调试补充。

@AGENTS.md
@README.md

## 终端调试速查（本项目专用）

```bash
# 测试（全绿才算完成，见 AGENTS.md §4）
python -m pytest tests/ -q            # 全部（26 单测 + 4 集成）
python -m pytest tests/unit -q        # 仅单测

# 语法检查（重依赖 torch/sko/ultralytics 未安装也能跑，懒加载设计）
find . -name "*.py" -not -path "./.history/*" | xargs python -m py_compile

# 服务（Docker 环境就绪后）
docker compose up -d                  # 起数据底座 + API + 采集 + 调度
curl -s http://localhost:8000/health  # 健康检查（依赖不可达应报 degraded）

# 脚本（部署/备份/重训只走脚本，AGENTS.md §5）
bash scripts/deploy.sh
```

## 调试时的项目现状（2026-07，骨架期）

- 重依赖（torch / scikit-opt / shap / ultralytics / asyncua）**未安装**：代码按懒加载设计，import 轻量模块和跑单测不受影响；调试到重依赖路径时先确认是否真的需要装。
- 数据库写入为预留接口：`data/collector/` 的 `write_tdengine` / `write_postgresql` 是占位，联调前需要先接 taospy/psycopg2 连接池。
- API 未接通的功能返回 `503 + detail`，这是**设计行为**（services 分域规范），不是 bug。
- 前端四模块（`frontend/*/`）只有规划 README，没有工程代码。
- 环境变量样例在 `.env.example`，调试前复制为 `.env` 并修改默认密码。

## 给 Claude 的特别提醒

- 修改任何代码前，先读本目录的嵌套 `AGENTS.md`（services/ data/ models/ frontend/ 各自有分域规则），并按根 AGENTS.md §0.3 对照表同步文档。
- 安全红线不可碰：`models/furnace_control/safety_limits.py` 钳位、换向窗口 2~3 分钟、RUL/数字孪生等"文档说后置"的功能不得擅自实现。
