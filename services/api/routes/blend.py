"""智能配煤系统路由（方案4.1节）。

- POST /blend/optimize  调配煤优化器：输入目标质量+可用煤种，输出3套推荐方案
- GET  /blend/recipes   历史配煤方案查询（PostgreSQL blend_recipe表）
- POST /blend/feedback  化验结果回流：对比预测误差，超阈值进入增量学习缓冲区（4.1.7节）
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from services.api.core.security import get_current_user
from services.api.db.connections import get_pg_conn
from services.api.schemas.blend import LabFeedback, OptimizeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/blend", tags=["智能配煤"])

# 增量学习触发阈值（4.1.7节）：误差超阈值入缓冲，缓冲区满则微调
ERROR_THRESHOLD = float(os.getenv("BLEND_ERROR_THRESHOLD", "2.0"))
BUFFER_TRIGGER_SIZE = int(os.getenv("BLEND_BUFFER_SIZE", "50"))

# 优化器单例（首次调用时装配，重依赖 scikit-opt/shap 懒加载）
_OPTIMIZER = None


def _get_optimizer():
    """装配并缓存 BlendingOptimizer 单例。

    质量预测走 QualityPredictor 门面（方案4.1.2模型A）：无 LightGBM 产物时自动
    路由经验模型（4.1.6 冷启动期），有产物且样本量达标后切 ML，路由层无需改动。
    依赖缺失（scikit-opt/shap 未安装）时抛 ImportError，由调用方转 503。
    """
    global _OPTIMIZER
    if _OPTIMIZER is None:
        from models.blending_optimizer.explainer import BlendExplainer  # noqa: PLC0415
        from models.blending_optimizer.optimizer import BlendingOptimizer  # noqa: PLC0415
        from models.quality_predictor.predict import QualityPredictor  # noqa: PLC0415

        predictor = QualityPredictor(mode=os.getenv("BLEND_PREDICTOR_MODE", "auto"))
        logger.info("质量预测后端: %s", predictor.active_backend)
        _OPTIMIZER = BlendingOptimizer(predictor, explainer=BlendExplainer(predictor))
    return _OPTIMIZER


# ---------- 接口 ----------

@router.post("/optimize", summary="调配煤优化器")
def optimize(req: OptimizeRequest, user: str = Depends(get_current_user)):
    """运行配煤优化：GA(scikit-opt)寻优 + 质量预测模型评估 + 边际贡献解释。

    返回3套方案：cost_optimal / quality_stable / balanced（4.1.5输出规范）。
    优化器本体在 models/blending_optimizer/，此处只做参数校验与调用编排。
    """
    # 前置可行性检查：各煤种配比上下限之和必须能覆盖[0,1]
    sum_min = sum(c.min_ratio for c in req.available_coals)
    sum_max = sum(c.max_ratio for c in req.available_coals)
    if sum_min > 1.0 or sum_max < 1.0:
        raise HTTPException(
            status_code=422,
            detail=f"配比约束无可行域：Σmin_ratio={sum_min:.2f}, Σmax_ratio={sum_max:.2f}",
        )
    try:
        from pydantic import ValidationError  # noqa: PLC0415

        from models.blending_optimizer.constraints import QualityTarget  # noqa: PLC0415
        from models.blending_optimizer.optimizer import (  # noqa: PLC0415
            AvailableCoal,
            OptimizeRequest as ModelOptimizeRequest,
        )

        optimizer = _get_optimizer()
        # 服务层契约 → 优化器契约：字段同名，lab_data 由自由 dict 收束为 CoalLabData
        model_req = ModelOptimizeRequest(
            target_quality=QualityTarget(**req.target_quality.model_dump()),
            available_coals=[AvailableCoal(**c.model_dump()) for c in req.available_coals],
            max_cost_per_ton=req.max_cost_per_ton,
            priority=req.priority,
        )
    except ImportError:
        logger.warning("配煤优化器依赖缺失（scikit-opt/shap 未安装），user=%s", user)
        raise HTTPException(status_code=503, detail="配煤优化器依赖未安装（scikit-opt/shap）")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"请求参数不满足优化器契约：{e}")

    try:
        resp = optimizer.optimize(model_req)
    except RuntimeError as e:
        # 三套方案均求解失败（约束过紧/库存不足），属请求层面问题
        raise HTTPException(status_code=422, detail=str(e))
    logger.info(
        "配煤优化完成: user=%s 方案数=%d 耗时=%dms",
        user, len(resp.solutions), resp.compute_time_ms,
    )
    return resp


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
    logger.warning("化验回流管道未就绪: batch_no=%s user=%s", fb.batch_no, user)
    raise HTTPException(
        status_code=503,
        detail="化验回流管道未就绪（预测值比对、误差缓冲与增量学习尚未接通）",
    )
