"""导出 FastAPI OpenAPI schema 到 frontend/shared/openapi.json（方案§6.1 前端契约链路）。

用途：前端各工程用 openapi-typescript 从该文件生成 TS 类型（frontend/AGENTS.md §2.1），
避免手写与后端重复的接口类型。后端路由变更后重新执行本脚本。

用法：
    python scripts/export_openapi.py

说明：
- 直接 import app 调 app.openapi()，不需要启动 uvicorn；
- 部分路由未声明 response_model，生成的 schema 会偏弱，属已知现实（frontend/AGENTS.md §2.1）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 仓库根目录加入 sys.path，保证能 import services.api.main
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "frontend" / "shared" / "openapi.json"


def main() -> None:
    """导出 OpenAPI schema 到 frontend/shared/openapi.json。

    --check：只比对不落盘，schema 与仓库内文件不一致时退出码 1（供 make check 使用）。
    """
    from services.api.main import app

    schema = app.openapi()
    fresh = json.dumps(schema, ensure_ascii=False, indent=2)
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != fresh:
            print("[check失败] openapi.json 已过期，请执行: python scripts/export_openapi.py")
            sys.exit(1)
        print(f"openapi.json 与当前路由一致（{len(schema.get('paths', {}))} 个路径）")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(fresh, encoding="utf-8")
    print(f"已导出 {len(schema.get('paths', {}))} 个路径 -> {OUTPUT}")


if __name__ == "__main__":
    main()
