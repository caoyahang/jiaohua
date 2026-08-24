#!/usr/bin/env bash
# =============================================================================
# check.sh - 变更后评审门禁（review 工序，总纲附录自检清单的机制化）
#
# 用法: ./scripts/check.sh [--full]
#   默认（快速）：pytest + 红线 grep + OpenAPI 契约新鲜度
#   --full：追加四个前端工程的 tsc --noEmit（需要各模块已 npm install）
#
# 任何一项失败即非零退出。pre-commit 钩子调用本脚本。
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

fail() { echo "[check失败] $1" >&2; exit 1; }

echo "===== 1/4 后端测试 ====="
python -m pytest tests/ -q

echo "===== 2/4 红线 grep ====="
# 红线1：furnace_ui 严禁出现「切手动」按钮（方案§4.2.6，切手动是 DCS 硬切换）
if grep -rn "切手动" frontend/furnace_ui/src --include="*.tsx" 2>/dev/null | grep -iE "button|onClick"; then
    fail "furnace_ui 出现疑似切手动按钮"
fi
# 红线2：前端禁止内联样式（height 为例外，frontend/AGENTS.md §3）
if grep -rn "style={{" frontend/*/src --include="*.tsx" 2>/dev/null | grep -v "height"; then
    fail "前端出现非例外内联样式"
fi
# 红线3：旧的认证模块路径不得复活（2026-08-15 分层后迁入 core/security.py）
if grep -rn "services\.api\.auth" --include="*.py" services/ tests/ 2>/dev/null; then
    fail "出现旧路径 services.api.auth 引用"
fi
# 红线4：前端 base 颜色 token 四模块同源（frontend/AGENTS.md 红线4）
python scripts/check_frontend_tokens.py || fail "前端 base colors 跨模块色值不一致"

echo "红线 grep 通过"

echo "===== 3/4 OpenAPI 契约新鲜度 ====="
python scripts/export_openapi.py --check

if [[ "${FULL}" == "1" ]]; then
    echo "===== 4/4 前端类型检查（--full） ====="
    for m in blend_ui furnace_ui pdm_ui dashboard; do
        if [[ -d "frontend/${m}/node_modules" ]]; then
            echo "--- ${m} ---"
            (cd "frontend/${m}" && npx tsc --noEmit)
        else
            echo "--- ${m} 未安装依赖，跳过 ---"
        fi
    done
else
    echo "===== 4/4 前端类型检查（跳过，--full 开启） ====="
fi

echo "===== check 全部通过 ====="
