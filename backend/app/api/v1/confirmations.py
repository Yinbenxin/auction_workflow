from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.confirmation import Confirmation
from app.schemas.confirmation import ConfirmationResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_confirmations(
    target_type: Optional[str] = Query(None, description="目标类型"),
    target_id: Optional[UUID] = Query(None, description="目标 ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """查询确认记录列表，按 target_type + target_id 过滤。"""
    stmt = select(Confirmation)
    if target_type is not None:
        stmt = stmt.where(Confirmation.target_type == target_type)
    if target_id is not None:
        stmt = stmt.where(Confirmation.target_id == target_id)
    stmt = stmt.order_by(Confirmation.confirmed_at.desc())

    result = await db.execute(stmt)
    rows = result.scalars().all()

    data: List[ConfirmationResponse] = [
        ConfirmationResponse.model_validate(row) for row in rows
    ]
    return {
        "code": 0,
        "data": [item.model_dump() for item in data],
        "message": "ok",
    }
