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
from app.models.retrospective import Retrospective
from app.schemas.retrospective import (
    RetrospectiveCreate,
    RetrospectiveResponse,
    RetrospectiveUpdate,
)
from app.services.retrospective_service import (
    get_retrospective_or_404,
    validate_retrospective_submit,
)

router = APIRouter()


async def _get_auction_or_404(auction_id: UUID, db: AsyncSession) -> Auction:
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "竞拍不存在"},
        )
    return auction


# ---------------------------------------------------------------------------
# GET /auctions/{auction_id}/retrospective
# ---------------------------------------------------------------------------


@router.get("/{auction_id}/retrospective", response_model=dict)
async def get_retrospective(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取复盘报告，不存在返回 404。"""
    await _get_auction_or_404(auction_id, db)
    retro = await get_retrospective_or_404(db, auction_id)
    return ok(data=RetrospectiveResponse.model_validate(retro).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/retrospective
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/retrospective", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_retrospective(
    auction_id: UUID,
    body: RetrospectiveCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("retrospective_owner")),
) -> dict:
    """创建复盘报告（retrospective_owner 角色）。
    前置校验：auction.phase_statuses["7"] == "completed"（竞拍执行已完成）。
    同一竞拍只允许一条复盘报告。
    """
    auction = await _get_auction_or_404(auction_id, db)

    if auction.phase_statuses.get("7") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "data": None,
                "message": "竞拍执行阶段（阶段7）尚未完成，无法创建复盘报告",
            },
        )

    # 同一竞拍只允许一条复盘报告
    existing = await db.execute(
        select(Retrospective).where(Retrospective.auction_id == auction_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "该竞拍已存在复盘报告"},
        )

    retro = Retrospective(
        auction_id=auction_id,
        strategy_version_id=body.strategy_version_id,
        basic_info=body.basic_info,
        strategy_summary=body.strategy_summary,
        execution_summary=body.execution_summary,
        transaction_result=body.transaction_result,
        deviation_analysis=body.deviation_analysis,
        anomaly_records=body.anomaly_records,
        confirmation_records=body.confirmation_records,
        root_cause=body.root_cause,
        improvement_actions=body.improvement_actions,
        strategy_learnings=body.strategy_learnings,
        emergency_explanation=body.emergency_explanation,
        status="draft",
        created_by=current_user.id,
    )
    db.add(retro)
    await db.flush()
    await db.refresh(retro)
    return ok(data=RetrospectiveResponse.model_validate(retro).model_dump())


# ---------------------------------------------------------------------------
# PUT /auctions/{auction_id}/retrospective
# ---------------------------------------------------------------------------


@router.put("/{auction_id}/retrospective", response_model=dict)
async def update_retrospective(
    auction_id: UUID,
    body: RetrospectiveUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("retrospective_owner")),
) -> dict:
    """更新复盘报告内容（retrospective_owner 角色）。
    status=submitted 时不允许修改。
    """
    await _get_auction_or_404(auction_id, db)
    retro = await get_retrospective_or_404(db, auction_id)

    if retro.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "复盘报告已归档，不允许修改"},
        )

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(retro, field, value)
    retro.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(retro)
    return ok(data=RetrospectiveResponse.model_validate(retro).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/retrospective/submit
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/retrospective/submit", response_model=dict)
async def submit_retrospective(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("retrospective_owner")),
) -> dict:
    """提交归档（retrospective_owner 角色）。
    执行 5 步校验，通过后：
    - status = submitted
    - submitted_at = now()
    - auction.phase_statuses["10"] = "archived"
    """
    auction = await _get_auction_or_404(auction_id, db)
    retro = await get_retrospective_or_404(db, auction_id)

    if retro.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "复盘报告已归档，不可重复提交"},
        )

    # 5 步校验
    await validate_retrospective_submit(auction_id, retro, db)

    now = datetime.now(timezone.utc)
    retro.status = "submitted"
    retro.submitted_at = now
    retro.updated_at = now

    phase_statuses = dict(auction.phase_statuses)
    phase_statuses["10"] = "archived"
    auction.phase_statuses = phase_statuses

    await db.flush()
    await db.refresh(retro)
    return ok(data=RetrospectiveResponse.model_validate(retro).model_dump())
