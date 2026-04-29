from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.confirmation import Confirmation
from app.models.strategy import StrategyVersion
from app.schemas.confirmation import ConfirmationResponse
from app.schemas.strategy import RejectRequest, StrategyCreate, StrategyResponse, StrategyUpdate
from app.services.strategy_service import (
    get_strategy_or_404,
    has_red_line_change,
    transition_status,
    update_with_optimistic_lock,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /auctions/{auction_id}/strategies
# ---------------------------------------------------------------------------


@router.get("", response_model=dict)
async def list_strategies(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """列出某竞拍下所有策略版本（含历史），按创建时间倒序。"""
    result = await db.execute(
        select(StrategyVersion)
        .where(StrategyVersion.auction_id == auction_id)
        .order_by(StrategyVersion.created_at.desc())
    )
    rows = result.scalars().all()
    return ok(data=[StrategyResponse.model_validate(r).model_dump() for r in rows])


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/strategies
# ---------------------------------------------------------------------------


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    auction_id: UUID,
    body: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("strategy_owner")),
) -> dict:
    """创建策略版本（strategy_owner 角色）。EMERGENCY 风险级别时 pre_authorized_actions 必填。"""
    if body.risk_level == "EMERGENCY" and not body.pre_authorized_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="风险级别为 EMERGENCY 时，pre_authorized_actions 必填",
        )

    sv = StrategyVersion(
        auction_id=auction_id,
        version_code=body.version_code,
        version_name=body.version_name,
        status="DRAFT",
        bid_price=body.bid_price,
        bid_quantity=body.bid_quantity,
        bid_time_points=body.bid_time_points,
        trigger_conditions=body.trigger_conditions,
        fallback_plan=body.fallback_plan,
        applicable_scenarios=body.applicable_scenarios,
        scenario_strategies=body.scenario_strategies,
        risk_level=body.risk_level,
        pre_authorized_actions=body.pre_authorized_actions,
        risk_notes=body.risk_notes,
        previous_version_id=body.previous_version_id,
        created_by=current_user.id,
    )
    db.add(sv)
    await db.flush()
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# GET /auctions/{auction_id}/strategies/{vid}
# ---------------------------------------------------------------------------


@router.get("/{vid}", response_model=dict)
async def get_strategy(
    auction_id: UUID,
    vid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取策略版本详情。"""
    sv = await get_strategy_or_404(db, auction_id, vid)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# PUT /auctions/{auction_id}/strategies/{vid}
# ---------------------------------------------------------------------------


@router.put("/{vid}", response_model=dict)
async def update_strategy(
    auction_id: UUID,
    vid: UUID,
    body: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("strategy_owner")),
) -> dict:
    """更新策略版本（仅 DRAFT 状态可直接更新）。红线字段变更且非 DRAFT 时返回 400。"""
    sv = await get_strategy_or_404(db, auction_id, vid)

    # 只保留非 None 的字段作为更新内容（version 字段单独处理）
    updates = {
        k: v
        for k, v in body.model_dump(exclude={"version"}).items()
        if v is not None
    }

    if sv.status != "DRAFT":
        if has_red_line_change(sv, updates):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="红线字段变更必须创建新版本",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态 {sv.status!r} 不允许直接更新，仅 DRAFT 状态可修改",
        )

    updates["updated_at"] = datetime.now(timezone.utc)
    await update_with_optimistic_lock(db, StrategyVersion, vid, body.version, updates)
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/strategies/{vid}/submit  DRAFT→PENDING
# ---------------------------------------------------------------------------


@router.post("/{vid}/submit", response_model=dict)
async def submit_strategy(
    auction_id: UUID,
    vid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """提交策略版本（DRAFT → PENDING）。"""
    sv = await get_strategy_or_404(db, auction_id, vid)
    try:
        transition_status(sv.status, "PENDING")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await update_with_optimistic_lock(
        db, StrategyVersion, vid, sv.version,
        {"status": "PENDING", "updated_at": datetime.now(timezone.utc)},
    )
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/strategies/{vid}/confirm  PENDING→CONFIRMED
# ---------------------------------------------------------------------------


@router.post("/{vid}/confirm", response_model=dict)
async def confirm_strategy(
    auction_id: UUID,
    vid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("auditor")),
) -> dict:
    """确认策略版本（PENDING → CONFIRMED）。审核人不得与提交人相同（双人复核）。"""
    sv = await get_strategy_or_404(db, auction_id, vid)

    if sv.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="审核人不得与策略创建人相同（双人复核制度）",
        )

    try:
        transition_status(sv.status, "CONFIRMED")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await update_with_optimistic_lock(
        db, StrategyVersion, vid, sv.version,
        {"status": "CONFIRMED", "updated_at": datetime.now(timezone.utc)},
    )

    # 写入确认记录
    confirmation = Confirmation(
        target_type="strategy_version",
        target_id=vid,
        action="confirm",
        confirmed_by=current_user.id,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/strategies/{vid}/reject  PENDING→DRAFT
# ---------------------------------------------------------------------------


@router.post("/{vid}/reject", response_model=dict)
async def reject_strategy(
    auction_id: UUID,
    vid: UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("auditor")),
) -> dict:
    """驳回策略版本（PENDING → DRAFT），并写入驳回记录。"""
    sv = await get_strategy_or_404(db, auction_id, vid)

    try:
        transition_status(sv.status, "DRAFT")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await update_with_optimistic_lock(
        db, StrategyVersion, vid, sv.version,
        {"status": "DRAFT", "updated_at": datetime.now(timezone.utc)},
    )

    # 写入驳回记录
    confirmation = Confirmation(
        target_type="strategy_version",
        target_id=vid,
        action="reject",
        comment=body.comment,
        confirmed_by=current_user.id,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/strategies/{vid}/finalize  CONFIRMED→FINAL
# ---------------------------------------------------------------------------


@router.post("/{vid}/finalize", response_model=dict)
async def finalize_strategy(
    auction_id: UUID,
    vid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("auditor")),
) -> dict:
    """标记最终版本（CONFIRMED → FINAL）。同一竞拍只能有一个 FINAL 版本。"""
    sv = await get_strategy_or_404(db, auction_id, vid)

    try:
        transition_status(sv.status, "FINAL")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # 检查是否已存在 FINAL 版本
    existing = await db.execute(
        select(StrategyVersion).where(
            StrategyVersion.auction_id == auction_id,
            StrategyVersion.status == "FINAL",
            StrategyVersion.id != vid,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该竞拍已存在 FINAL 版本，不能重复标记",
        )

    await update_with_optimistic_lock(
        db, StrategyVersion, vid, sv.version,
        {"status": "FINAL", "updated_at": datetime.now(timezone.utc)},
    )
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/strategies/{vid}/void  任意非VOIDED→VOIDED
# ---------------------------------------------------------------------------


@router.post("/{vid}/void", response_model=dict)
async def void_strategy(
    auction_id: UUID,
    vid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """作废策略版本（任意非 VOIDED 状态 → VOIDED）。历史记录保留。"""
    sv = await get_strategy_or_404(db, auction_id, vid)

    try:
        transition_status(sv.status, "VOIDED")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await update_with_optimistic_lock(
        db, StrategyVersion, vid, sv.version,
        {"status": "VOIDED", "updated_at": datetime.now(timezone.utc)},
    )
    await db.refresh(sv)
    return ok(data=StrategyResponse.model_validate(sv).model_dump())


# ---------------------------------------------------------------------------
# GET /auctions/{auction_id}/strategies/{vid}/confirmations
# ---------------------------------------------------------------------------


@router.get("/{vid}/confirmations", response_model=dict)
async def list_strategy_confirmations(
    auction_id: UUID,
    vid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """查看策略版本的确认/驳回记录。"""
    # 先确认策略版本存在且属于该竞拍
    await get_strategy_or_404(db, auction_id, vid)

    result = await db.execute(
        select(Confirmation)
        .where(
            Confirmation.target_type == "strategy_version",
            Confirmation.target_id == vid,
        )
        .order_by(Confirmation.confirmed_at.desc())
    )
    rows = result.scalars().all()
    return ok(data=[ConfirmationResponse.model_validate(r).model_dump() for r in rows])
