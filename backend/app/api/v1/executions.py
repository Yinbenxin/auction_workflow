from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import require_role
from app.models.auction import Auction
from app.models.execution import ExecutionLog
from app.schemas.execution import ExecutionLogCreate, ExecutionLogResponse

router = APIRouter()


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


@router.get("/{auction_id}/execution-logs", response_model=dict)
async def list_execution_logs(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取指定竞拍的执行日志列表，按 triggered_at 升序排列。"""
    stmt = (
        select(ExecutionLog)
        .where(ExecutionLog.auction_id == auction_id)
        .order_by(ExecutionLog.triggered_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    data: List[ExecutionLogResponse] = [
        ExecutionLogResponse.model_validate(row) for row in rows
    ]
    return ok(data=[item.model_dump() for item in data])


@router.post("/{auction_id}/execution-logs", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_execution_log(
    auction_id: UUID,
    body: ExecutionLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """新增执行日志条目。前置校验：竞拍阶段 6 必须为 executable。"""
    # 查询竞拍
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction: Auction | None = result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "竞拍不存在"},
        )

    # 前置校验：阶段 6 必须标记为 executable
    if auction.phase_statuses.get("6") != "executable":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": 422, "data": None, "message": "竞拍尚未标记为可执行（阶段 6 需为 executable）"},
        )

    log = ExecutionLog(
        auction_id=auction_id,
        task_number=body.task_number,
        triggered_at=body.triggered_at,
        bid_price=body.bid_price,
        bid_quantity=body.bid_quantity,
        system_status=body.system_status,
        data_feed_status=body.data_feed_status,
        result=body.result,
        notes=body.notes,
        logged_by=current_user.id,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)

    return ok(
        data=ExecutionLogResponse.model_validate(log).model_dump(),
        message="执行日志已创建",
    )


@router.post("/{auction_id}/execution-complete", response_model=dict)
async def mark_execution_complete(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """标记竞拍执行完成，更新 phase_statuses["7"] = "completed"。
    前置校验：至少存在一条执行日志。
    """
    # 查询竞拍
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction: Auction | None = result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "竞拍不存在"},
        )

    # 前置校验：至少有一条执行日志
    log_result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.auction_id == auction_id)
        .limit(1)
    )
    if log_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": 422, "data": None, "message": "尚无执行日志，无法标记执行完成"},
        )

    # 更新 phase_statuses["7"] = "completed"
    updated_statuses = dict(auction.phase_statuses)
    updated_statuses["7"] = "completed"
    auction.phase_statuses = updated_statuses

    return ok(message="竞拍执行已标记为完成")
