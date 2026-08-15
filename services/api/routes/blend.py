"""智能配煤系统路由（方案4.1节）。

- POST /blend/optimize  调配煤优化器：输入目标质量+可用煤种，输出3套推荐方案
- GET  /blend/recipes   历史配煤方案查询（PostgreSQL blend_recipe表）
- POST /blend/feedback  化验结果回流：对比预测误差，超阈值进入增量学习缓冲区（4.1.7节）
"""

import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException

from services.api.core.security import get_current_user
from services.api.db.connections import get_pg_conn
from services.api.schemas.blend import LabFeedback, OptimizeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/blend", tags=["智能配煤"])

# 增量学习触发阈值（4.1.7节）：误差超阈值入缓冲，缓冲区满则微调
ERROR_THRESHOLD = float(os.getenv("BLEND_ERROR_THRESHOLD", "2.0"))
BUFFER_TRIGGER_SIZE = int(os.getenv("BLEND_BUFFER_SIZE", "50"))


# ---------- 接口 ----------

@router.post("/optimize", summary="调配煤优化器")
def optimize(req: OptimizeRequest, user: str = Depends(get_current_user)):
    """运行配煤优化：GA(scikit-opt)寻优 + 质量预测模型(LightGBM)评估 + SHAP解释。

    返回3套方案：cost_optimal / quality_stable / balanced（4.1.5输出规范）。
    优化器本体在 models/blending_optimizer/，此处只做参数校验与调用编排。
    """
    start = time.time()
    # 前置可行性检查：各煤种配比上下限之和必须能覆盖[0,1]
    sum_min = sum(c.min_ratio for c in req.available_coals)
    sum_max = sum(c.max_ratio for c in req.available_coals)
    if sum_min > 1.0 or sum_max < 1.0:
        raise HTTPException(
            status_code=422,
            detail=f"配比约束无可行域：Σmin_ratio={sum_min:.2f}, Σmax_ratio={sum_max:.2f}",
        )
    try:
        from models.blending_optimizer.optimizer import BlendingOptimizer  # noqa: PLC0415
    except ImportError:
        logger.warning("配煤优化器模块尚未就绪，user=%s", user)
        raise HTTPException(status_code=503, detail="配煤优化器未部署（models.blending_optimizer缺失）")
    # TODO: 加载质量预测模型(MLflow注册表) → BlendingOptimizer(req).run() → SHAP解释
    raise HTTPException(status_code=503, detail="质量预测模型尚未注册（冷启动期用经验模型，见4.1.6）")


@router.get("/recipes", summary="历史配煤方案查询")
def list_recipes(
    furnace_id: int | None = None,
    limit: int = 50,
    user: str = Depends(get_current_user),
):
    """查询PostgreSQL blend_recipe表（3.4.1节），支持按焦炉号过滤。"""
    import psycopg2.extras  # noqa: PLC0415

    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = "SELECT * FROM blend_recipe"
            params: list = []
            if furnace_id is not None:
                sql += " WHERE furnace_id = %s"
                params.append(furnace_id)
            sql += " ORDER BY id DESC LIMIT %s"
            params.append(limit)
            cur.execute(sql, params)
            return {"recipes": [dict(r) for r in cur.fetchall()]}
    finally:
        conn.close()


@router.post("/feedback", summary="化验结果回流，触发增量学习")
def feedback(fb: LabFeedback, user: str = Depends(get_current_user)):
    """化验数据闭环（4.1.7节）：

    1. 取该批次当时的预测值 → 2. 计算误差 → 3. 超阈值写入误差缓冲区(Redis)
    → 4. 缓冲区满 BUFFER_TRIGGER_SIZE 条触发增量微调（LightGBM热启动，小学习率防遗忘）。
    """
    # TODO: 从blend_recipe表取该批次predicted_quality；不存在则404
    # TODO: 逐指标计算误差，任一超ERROR_THRESHOLD则lpush到Redis误差缓冲区
    # TODO: 缓冲区长度>=BUFFER_TRIGGER_SIZE时调用IncrementalLearner._incremental_train()
    logger.info("化验回流接收: batch_no=%s user=%s", fb.batch_no, user)
    return {
        "batch_no": fb.batch_no,
        "status": "accepted",
        "detail": "已接收，待与预测值比对（增量学习管道待接通）",
    }
