"""pytest全局配置。

- 将项目根目录加入sys.path，使 tests 可 import services/data/models 包
- 清空数据库连接环境变量，验证 /health 能明确报告 degraded
- 显式注入测试专用认证配置，禁止依赖生产代码的默认账号或密钥
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 测试环境不依赖真实数据库：未配置连接串时健康检查跳过对应依赖
for var in ("DATABASE_URL", "REDIS_URL", "TDENGINE_URL"):
    os.environ.pop(var, None)

os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-key"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"
