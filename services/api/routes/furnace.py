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

# 设定值安全钳位区间（软件层，DCS侧另有硬钳位）——示例值，按炉型标定
SAFETY_LIMITS = {
    "gas_flow": {"min": 8000.0, "max": 20000.0, "max_delta": 500.0},   # m³/h，单步最大变化量
    "flue_suction": {"min": 80.0, "max": 220.0, "max_delta": 10.0},    # Pa
}

VALID_MODES = ("manual", "shadow", "auto")


def clamp_setpoint(name: str, value: float, last_value: float) -> tuple[float, bool]:
    """设定值钳位：先限单步变化速率，再限绝对上下限。

    返回 (钳位后值, 是否发生过钳位)。这是软件层双保险；
    真正的安全钳位在DCS侧硬回路实现（4.2.6节）。
    """
    limits = SAFETY_LIMITS[name]
    clamped = False
    delta = value - last_value
    if abs(delta) > limits["max_delta"]:
        value = last_value + limits["max_delta"] * (1 if delta > 0 else -1)
        clamped = True
    if not limits["min"] <= value <= limits["max"]:
        value = min(max(value, limits["min"]), limits["max"])
        clamped = True
    return round(value, 2), clamped


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
    # TODO: 读取当前控制模式；manual模式直接返回空建议
    # TODO: 调用 models.furnace_control.mpc_controller 求解 raw_setpoint
    # 示例：raw_gas_flow = mpc.solve(...); 以下为占位值
    raw_gas_flow, last_gas_flow = 15500.0, 15200.0
    gas_flow, clamped = clamp_setpoint("gas_flow", raw_gas_flow, last_gas_flow)
    if clamped:
        logger.warning("furnace=%s 设定值被钳位: raw=%s -> %s", furnace_id, raw_gas_flow, gas_flow)
    return {
        "furnace_id": furnace_id,
        "gas_flow_setpoint": gas_flow,
        "clamped": clamped,
        "model_version": None,  # TODO: MLflow模型版本
    }


@router.post("/control-mode", summary="切换控制模式")
def set_control_mode(req: ControlModeRequest, user: str = Depends(get_current_user)):
    """切换 manual/shadow/auto。

    状态存Redis（key: furnace:control_mode:{furnace_id}），Redis不可用时落内存。
    注意：「一键切手动」为DCS硬切换（4.2.6节），本接口只是AI系统侧的模式记录，
    不构成安全通路。
    """
    key = f"furnace:control_mode:{req.furnace_id}"
    r = get_redis()
    if r is not None:
        try:
            r.set(key, req.mode)
        except Exception as exc:
            logger.error("Redis写入失败，模式仅记录到日志: %s", exc)
    else:
        logger.error("Redis不可用，模式仅记录到日志")
    logger.info(
        "控制模式切换: furnace=%s mode=%s operator=%s api_user=%s reason=%s",
        req.furnace_id, req.mode, req.operator, user, req.reason,
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
