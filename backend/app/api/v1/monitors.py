from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import require_role
from app.models.monitor import MonitorRecord
from app.schemas.monitor import MonitorRecordCreate, MonitorRecordResponse

router = APIRouter()


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


@router.get("", response_model=dict)
async def list_monitor_records(
    auction_id: UUID,
    record_type: Optional[str] = Query(None, description="过滤类型：normal / anomaly"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取指定竞拍的监控记录列表，按 recorded_at 倒序。"""
    stmt = select(MonitorRecord).where(MonitorRecord.auction_id == auction_id)
    if record_type is not None:
        stmt = stmt.where(MonitorRecord.record_type == record_type)
    stmt = stmt.order_by(MonitorRecord.recorded_at.desc())

    result = await db.execute(stmt)
    rows = result.scalars().all()

    data: List[MonitorRecordResponse] = [
        MonitorRecordResponse.model_validate(row) for row in rows
    ]
    return ok(data=[item.model_dump() for item in data])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_monitor_record(
    auction_id: UUID,
    body: MonitorRecordCreate,
    current_user=Depends(require_role("monitor")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """新增监控记录（仅 monitor 角色）。record_type=anomaly 时 anomaly_type 必填。"""
    if body.record_type == "anomaly" and not body.anomaly_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": 422, "data": None, "message": "异常记录必须填写 anomaly_type"},
        )

    record = MonitorRecord(
        auction_id=auction_id,
        record_type=body.record_type,
        price_change=body.price_change,
        remaining_quantity=body.remaining_quantity,
        transaction_speed=body.transaction_speed,
        data_feed_normal=body.data_feed_normal,
        system_normal=body.system_normal,
        anomaly_type=body.anomaly_type,
        anomaly_action=body.anomaly_action,
        recorded_by=current_user.id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    return ok(
        data=MonitorRecordResponse.model_validate(record).model_dump(),
        message="监控记录已创建",
    )
