"""焦炉AI智能加热控制路由（方案4.2节）。

- GET  /furnace/temp           实时炉温（TDengine furnace_temp表，3.4.3节）
- GET  /furnace/ai-setpoint    AI设定值建议（经safety_limits钳位，4.2.6节安全红线）
- POST /furnace/control-mode   切换 manual/shadow/auto 三阶段控制模式（4.2.2节）
- GET  /furnace/k-coefficients 热工K系数：K均/K安/K1/K2/K3（4.2.6节）

安全红线（4.2.6节）：AI只输出设定值，设定值上下限与变化速率在DCS侧硬钳位；
本服务的钳位是软件层双保险，安全联锁永远走DCS硬回路，AI无权触碰。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from services.api.core.security import get_current_user
from services.api.db.connections import get_redis, get_td_conn
from services.api.schemas.furnace import ControlModeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/furnace", tags=["焦炉加热控制"])


def _clamp_ai_setpoints(
    *,
    gas_flow: float,
    flue_draft: float,
    collector_pressure: float,
    current_gas_flow: float,
    current_flue_draft: float,
    current_collector_pressure: float,
) -> dict[str, float]:
    """通过安全红线模块统一钳位 MPC 输出（方案§4.2.6）。

    Args:
        gas_flow: MPC 建议煤气流量，m³/h。
        flue_draft: MPC 建议分烟道吸力，Pa。
        collector_pressure: MPC 建议集气管压力，Pa。
        current_gas_flow: 当前有效煤气流量设定值，m³/h。
        current_flue_draft: 当前有效分烟道吸力设定值，Pa。
        current_collector_pressure: 当前有效集气管压力设定值，Pa。

    Returns:
        经过 ``models/furnace_control/safety_limits.py`` 钳位后的三通道设定值。

    该函数是服务层唯一允许使用的 AI 设定值出口，不在路由层复制任何限值。
    """
    from models.furnace_control.safety_limits import clamp_all  # noqa: PLC0415

    return clamp_all(
        gas_flow=gas_flow,
        flue_draft=flue_draft,
        collector_pressure=collector_pressure,
        current_gas_flow=current_gas_flow,
        current_flue_draft=current_flue_draft,
        current_collector_pressure=current_collector_pressure,
    )


@router.get("/temp", summary="实时炉温")
def get_temp(furnace_id: int, user: str = Depends(get_current_user)):
    """查询TDengine中该焦炉最近一次的机/焦侧火道温度。

    注意：换向前后2~3分钟数据为脏数据（4.2.6节），
    由ETL管道打标记，此处查询应过滤 switching_flag=0。
    """
    conn = get_td_conn()  # TODO: 连接池化管理
    # TODO: SELECT last(*) FROM furnace_temp WHERE furnace_id=? AND switching_flag=0
    conn.close()
    raise HTTPException(status_code=503, detail="炉温查询SQL待实现（依赖3.4.3建表）")


@router.get("/ai-setpoint", summary="AI设定值建议")
def get_ai_setpoint(furnace_id: int, user: str = Depends(get_current_user)):
    """MPC求解最优煤气流量/吸力设定值（4.2.4节），输出前经 clamp_setpoint 钳位。

    shadow模式下仅展示不下发；auto模式由控制回路消费本接口结果。
    """
    # 未接通实时工况、MPC 产物与模型版本前，禁止用示例值冒充 AI 输出。
    # 正式接通时，MPC 原始输出必须先经过 _clamp_ai_setpoints() 再返回/下发。
    raise HTTPException(
        status_code=503,
        detail="AI设定值服务未就绪（实时工况、MPC模型或模型版本缺失）",
    )


@router.post("/control-mode", summary="切换控制模式")
def set_control_mode(req: ControlModeRequest, user: str = Depends(get_current_user)):
    """切换 manual/shadow/auto。

    状态存Redis（key: furnace:control_mode:{furnace_id}），Redis不可用时落内存。
    注意：「一键切手动」为DCS硬切换（4.2.6节），本接口只是AI系统侧的模式记录，
    不构成安全通路。
    """
    key = f"furnace:control_mode:{req.furnace_id}"
    r = get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="控制模式存储不可用（Redis未配置）")
    try:
        r.set(key, req.mode)
    except Exception as exc:
        logger.exception("Redis写入控制模式失败")
        raise HTTPException(status_code=503, detail="控制模式存储不可用") from exc
    logger.info(
        "控制模式切换: furnace=%s mode=%s operator=%s reviewer=%s api_user=%s reason=%s",
        req.furnace_id, req.mode, req.operator, req.reviewer, user, req.reason,
    )
    return {"furnace_id": req.furnace_id, "mode": req.mode, "status": "ok"}


@router.get("/k-coefficients", summary="热工K系数查询")
def get_k_coefficients(furnace_id: int, shift_date: str | None = None,
                       user: str = Depends(get_current_user)):
    """返回K均/K安/K1/K2/K3（4.2.6节统一考核口径）。

    计算逻辑在 data/pipeline/k_coefficients.py（直行温度记录+推焦计划/执行记录），
    本接口只做查询编排。
    """
    try:
        from data.pipeline.k_coefficients import compute_all  # noqa: PLC0415
    except ImportError:
        raise HTTPException(status_code=503, detail="K系数计算模块未部署")
    # TODO: 从TDengine/PostgreSQL取直行温度与推焦记录 → compute_all(...)
    raise HTTPException(status_code=503, detail="K系数数据源待接通")
