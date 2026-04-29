from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.auction import Auction
from app.models.confirmation import Confirmation
from app.schemas.auction import (
    AuctionCreate,
    AuctionResponse,
    BasicInfoUpdate,
    HistoryAnalysisUpdate,
)
from app.services.strategy_service import update_with_optimistic_lock

router = APIRouter()

# ---------------------------------------------------------------------------
# 阶段门控
# ---------------------------------------------------------------------------

PHASE_GATES: dict[int, object] = {
    2: lambda a: a.phase_statuses.get("1") == "confirmed",
    3: lambda a: True,  # 软阻断，允许继续
    5: lambda a: a.phase_statuses.get("4") == "has_final_strategy",
    6: lambda a: a.phase_statuses.get("5") == "confirmed",
    7: lambda a: a.phase_statuses.get("6") == "passed",
    10: lambda a: a.phase_statuses.get("7") == "completed",
}


def check_phase_gate(auction: Auction, target_phase: int) -> None:
    """校验前置阶段是否满足，不满足时抛 HTTP 400。"""
    gate = PHASE_GATES.get(target_phase)
    if gate and not gate(auction):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"前置阶段未完成，无法进入阶段 {target_phase}",
        )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


async def get_auction_or_404(db: AsyncSession, auction_id: UUID) -> Auction:
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="竞拍项目不存在",
        )
    return auction


# ---------------------------------------------------------------------------
# GET /auctions — 竞拍项目列表
# ---------------------------------------------------------------------------


@router.get("", response_model=dict)
async def list_auctions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """列出所有竞拍项目，按竞拍日期倒序。"""
    result = await db.execute(
        select(Auction).order_by(Auction.auction_date.desc())
    )
    rows = result.scalars().all()
    return ok(data=[AuctionResponse.model_validate(r).model_dump() for r in rows])


# ---------------------------------------------------------------------------
# POST /auctions — 创建竞拍项目
# ---------------------------------------------------------------------------


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_auction(
    body: AuctionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("business_owner")),
) -> dict:
    """创建竞拍项目（business_owner 角色）。初始化 phase_statuses={}, current_phase=1。"""
    auction = Auction(
        name=body.name,
        auction_date=body.auction_date,
        current_phase=1,
        phase_statuses={},
        basic_info={},
        history_analysis={},
        version=0,
        created_by=current_user.id,
    )
    db.add(auction)
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# GET /auctions/{id} — 竞拍项目详情
# ---------------------------------------------------------------------------


@router.get("/{auction_id}", response_model=dict)
async def get_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取竞拍项目详情（含阶段状态）。"""
    auction = await get_auction_or_404(db, auction_id)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# PUT /auctions/{id}/basic-info — 更新阶段01基础信息
# ---------------------------------------------------------------------------


@router.put("/{auction_id}/basic-info", response_model=dict)
async def update_basic_info(
    auction_id: UUID,
    body: BasicInfoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("business_owner")),
) -> dict:
    """更新阶段01基础信息（business_owner 角色），使用乐观锁。"""
    auction = await get_auction_or_404(db, auction_id)
    await update_with_optimistic_lock(
        db,
        Auction,
        auction_id,
        body.version,
        {
            "basic_info": body.basic_info,
            "updated_at": datetime.now(timezone.utc),
        },
    )
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{id}/basic-info/confirm — 确认阶段01基础信息
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/basic-info/confirm", response_model=dict)
async def confirm_basic_info(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("business_owner")),
) -> dict:
    """确认阶段01基础信息（business_owner 角色）。更新 phase_statuses["1"]="confirmed"，写入确认记录。"""
    auction = await get_auction_or_404(db, auction_id)

    new_statuses = {**auction.phase_statuses, "1": "confirmed"}
    await update_with_optimistic_lock(
        db,
        Auction,
        auction_id,
        auction.version,
        {
            "phase_statuses": new_statuses,
            "updated_at": datetime.now(timezone.utc),
        },
    )

    confirmation = Confirmation(
        target_type="auction_basic_info",
        target_id=auction_id,
        action="confirm",
        confirmed_by=current_user.id,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# PUT /auctions/{id}/history-analysis — 更新阶段02历史分析数据
# ---------------------------------------------------------------------------


@router.put("/{auction_id}/history-analysis", response_model=dict)
async def update_history_analysis(
    auction_id: UUID,
    body: HistoryAnalysisUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("data_analyst")),
) -> dict:
    """更新阶段02历史分析数据（data_analyst 角色）。前置校验阶段门控，使用乐观锁。"""
    auction = await get_auction_or_404(db, auction_id)
    check_phase_gate(auction, 2)

    await update_with_optimistic_lock(
        db,
        Auction,
        auction_id,
        body.version,
        {
            "history_analysis": body.history_analysis,
            "updated_at": datetime.now(timezone.utc),
        },
    )
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{id}/history-analysis/confirm — 确认阶段02历史分析
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/history-analysis/confirm", response_model=dict)
async def confirm_history_analysis(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("strategy_owner")),
) -> dict:
    """确认阶段02历史分析（strategy_owner 角色）。更新 phase_statuses["2"]="confirmed"，写入确认记录。"""
    auction = await get_auction_or_404(db, auction_id)

    new_statuses = {**auction.phase_statuses, "2": "confirmed"}
    await update_with_optimistic_lock(
        db,
        Auction,
        auction_id,
        auction.version,
        {
            "phase_statuses": new_statuses,
            "updated_at": datetime.now(timezone.utc),
        },
    )

    confirmation = Confirmation(
        target_type="history_analysis",
        target_id=auction_id,
        action="confirm",
        confirmed_by=current_user.id,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())
