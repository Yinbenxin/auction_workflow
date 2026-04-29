from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modification import Modification

# ---------------------------------------------------------------------------
# 状态机
# ---------------------------------------------------------------------------

MOD_VALID_TRANSITIONS: dict[str, list[str]] = {
    "DRAFT": ["PENDING_APPROVAL"],
    "PENDING_APPROVAL": ["REJECTED", "PENDING_REVIEW"],
    "REJECTED": [],  # 终态
    "PENDING_REVIEW": ["APPROVED", "REJECTED"],
    "APPROVED": ["EXECUTED"],
    "EXECUTED": [],  # 终态
    "EMERGENCY_EXECUTED": ["PENDING_POST_EXPLANATION", "PENDING_DEVIATION_EXPLANATION"],
    "PENDING_POST_EXPLANATION": ["POST_EXPLAINED"],
    "PENDING_DEVIATION_EXPLANATION": ["POST_EXPLAINED"],
    "POST_EXPLAINED": [],  # 终态
}


def transition_mod_status(current: str, target: str) -> None:
    """校验临场修改状态流转是否合法，非法时抛 HTTPException 400。"""
    allowed = MOD_VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"不允许从 {current!r} 流转到 {target!r}，"
                f"合法目标状态：{allowed or '无（终态）'}"
            ),
        )


async def get_modification_or_404(
    session: AsyncSession,
    auction_id: UUID,
    modification_id: UUID,
) -> Modification:
    """按 auction_id + id 查询临场修改记录，不存在时抛 404。"""
    result = await session.execute(
        select(Modification).where(
            Modification.id == modification_id,
            Modification.auction_id == auction_id,
        )
    )
    mod = result.scalar_one_or_none()
    if mod is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="临场修改记录不存在",
        )
    return mod
