"""pytest全局配置。

- 将项目根目录加入sys.path，使 tests 可 import services/data/models 包
- 清空数据库连接环境变量，保证 /health 等测试在无库环境下确定性通过
  （依赖未配置时健康检查视为跳过，返回 ok）
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 测试环境不依赖真实数据库：未配置连接串时健康检查跳过对应依赖
for var in ("DATABASE_URL", "REDIS_URL", "TDENGINE_URL"):
    os.environ.pop(var, None)
