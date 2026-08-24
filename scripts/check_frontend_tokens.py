#!/usr/bin/env python3
"""前端颜色 token 防漂移检查（frontend/AGENTS.md 红线4 的机制化）。

规则：
- 四模块 `src/styles/tokens.ts` 的 base `colors` 组必须**同源**——
  同名 key 的色值跨模块一致（扩展只允许新增 key，且放进独立导出组，
  如 dashboard 的 darkColors、pdm_ui 的 orange）。
- 发现同名不同值即失败退出（这就是"同一个事实两个口径"，总纲 §0.1）。

用法：python scripts/check_frontend_tokens.py（由 scripts/check.sh 调用）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ("blend_ui", "furnace_ui", "pdm_ui", "dashboard")

# 提取 export const colors = { ... } 块内的  key: '#hex'  对
BLOCK_RE = re.compile(r"export const colors = \{(.*?)\} as const", re.S)
PAIR_RE = re.compile(r"(\w+):\s*'(#[0-9a-fA-F]{3,8})'")


def parse_base_colors(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    m = BLOCK_RE.search(text)
    if not m:
        raise SystemExit(f"[token检查失败] {path} 缺少 export const colors 块")
    return dict(PAIR_RE.findall(m.group(1)))


def main() -> int:
    # key -> {模块: 色值}
    seen: dict[str, dict[str, str]] = {}
    for mod in MODULES:
        colors = parse_base_colors(ROOT / "frontend" / mod / "src" / "styles" / "tokens.ts")
        for key, hexval in colors.items():
            seen.setdefault(key, {})[mod] = hexval.lower()

    conflicts = {
        key: vals for key, vals in seen.items() if len(set(vals.values())) > 1
    }
    if conflicts:
        print("[token检查失败] base colors 跨模块色值不一致：", file=sys.stderr)
        for key, vals in conflicts.items():
            print(f"  {key}: {vals}", file=sys.stderr)
        print("修复：统一色值，或把差异改为模块独立扩展组（frontend/AGENTS.md 红线4）", file=sys.stderr)
        return 1
    print(f"前端 token 检查通过（{len(MODULES)} 模块，{len(seen)} 个 base 色值一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
