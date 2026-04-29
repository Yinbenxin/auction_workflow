from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.modification import Modification
from app.schemas.modification import (
    ApproveRequest,
    EmergencyExecuteRequest,
    ExecuteRequest,
    ModificationCreate,
    ModificationResponse,
    PostExplanationRequest,
    RejectRequest,
    ReviewRequest,
)
from app.services.modification_service import (
    get_modification_or_404,
    transition_mod_status,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /auctions/{auction_id}/modifications
# ---------------------------------------------------------------------------


@router.get("", response_model=dict)
async def list_modifications(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """列出某竞拍下所有临场修改申请，按创建时间倒序。"""
    result = await db.execute(
        select(Modification)
        .where(Modification.auction_id == auction_id)
        .order_by(Modification.created_at.desc())
    )
    rows = result.scalars().all()
    return ok(data=[ModificationResponse.model_validate(r).model_dump() for r in rows])


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications
# ---------------------------------------------------------------------------


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_modification(
    auction_id: UUID,
    body: ModificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader", "monitor")),
) -> dict:
    """提交临场修改申请（trader/monitor 角色）。reason 和 impact_scope 必填。"""
    now = datetime.now(timezone.utc)
    mod = Modification(
        auction_id=auction_id,
        strategy_version_id=body.strategy_version_id,
        status="PENDING_APPROVAL",
        affected_fields=body.affected_fields,
        before_value=body.before_value,
        after_value=body.after_value,
        reason=body.reason,
        impact_scope=body.impact_scope,
        risk_notes=body.risk_notes,
        is_emergency=False,
        attachments=body.attachments,
        requested_by=current_user.id,
        requested_at=now,
    )
    db.add(mod)
    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/emergency-execute
# ---------------------------------------------------------------------------


@router.post(
    "/emergency-execute",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def emergency_execute(
    auction_id: UUID,
    body: EmergencyExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """应急执行（trader 角色）。
    命中预授权规则 → PENDING_POST_EXPLANATION；
    未命中 → PENDING_DEVIATION_EXPLANATION。
    """
    now = datetime.now(timezone.utc)

    if body.is_pre_authorized:
        initial_status = "PENDING_POST_EXPLANATION"
    else:
        initial_status = "PENDING_DEVIATION_EXPLANATION"

    mod = Modification(
        auction_id=auction_id,
        strategy_version_id=body.strategy_version_id,
        status=initial_status,
        affected_fields=body.affected_fields,
        before_value=body.before_value,
        after_value=body.after_value,
        reason=body.reason,
        impact_scope=body.impact_scope,
        is_emergency=True,
        is_pre_authorized=body.is_pre_authorized,
        matched_emergency_rule_id=body.matched_emergency_rule_id,
        attachments=[],
        requested_by=current_user.id,
        requested_at=now,
    )
    db.add(mod)
    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/{mid}/approve
# ---------------------------------------------------------------------------


@router.post("/{mid}/approve", response_model=dict)
async def approve_modification(
    auction_id: UUID,
    mid: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("strategy_owner")),
) -> dict:
    """审批通过（strategy_owner 角色）。PENDING_APPROVAL → PENDING_REVIEW。"""
    mod = await get_modification_or_404(db, auction_id, mid)
    transition_mod_status(mod.status, "PENDING_REVIEW")

    now = datetime.now(timezone.utc)
    mod.status = "PENDING_REVIEW"
    mod.approved_by = current_user.id
    mod.approved_at = now
    mod.approval_comment = body.approval_comment
    mod.updated_at = now

    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/{mid}/reject
# ---------------------------------------------------------------------------


@router.post("/{mid}/reject", response_model=dict)
async def reject_modification(
    auction_id: UUID,
    mid: UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("strategy_owner")),
) -> dict:
    """审批驳回（strategy_owner 角色）。
    PENDING_APPROVAL → REJECTED 或 PENDING_REVIEW → REJECTED。
    """
    mod = await get_modification_or_404(db, auction_id, mid)
    transition_mod_status(mod.status, "REJECTED")

    now = datetime.now(timezone.utc)
    mod.status = "REJECTED"
    mod.updated_at = now

    if mod.status == "PENDING_APPROVAL":
        mod.approved_by = current_user.id
        mod.approved_at = now
        mod.approval_comment = body.comment
    else:
        # PENDING_REVIEW → REJECTED 由 strategy_owner 驳回时记录 reviewed_by
        mod.reviewed_by = current_user.id
        mod.reviewed_at = now
        mod.review_comment = body.comment

    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/{mid}/review
# ---------------------------------------------------------------------------


@router.post("/{mid}/review", response_model=dict)
async def review_modification(
    auction_id: UUID,
    mid: UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("reviewer")),
) -> dict:
    """复核通过（reviewer 角色）。PENDING_REVIEW → APPROVED。"""
    mod = await get_modification_or_404(db, auction_id, mid)
    transition_mod_status(mod.status, "APPROVED")

    now = datetime.now(timezone.utc)
    mod.status = "APPROVED"
    mod.reviewed_by = current_user.id
    mod.reviewed_at = now
    mod.review_comment = body.review_comment
    mod.updated_at = now

    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/{mid}/review-reject
# ---------------------------------------------------------------------------


@router.post("/{mid}/review-reject", response_model=dict)
async def review_reject_modification(
    auction_id: UUID,
    mid: UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("reviewer")),
) -> dict:
    """复核驳回（reviewer 角色）。PENDING_REVIEW → REJECTED。"""
    mod = await get_modification_or_404(db, auction_id, mid)
    transition_mod_status(mod.status, "REJECTED")

    now = datetime.now(timezone.utc)
    mod.status = "REJECTED"
    mod.reviewed_by = current_user.id
    mod.reviewed_at = now
    mod.review_comment = body.review_comment
    mod.updated_at = now

    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/{mid}/execute
# ---------------------------------------------------------------------------


@router.post("/{mid}/execute", response_model=dict)
async def execute_modification(
    auction_id: UUID,
    mid: UUID,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """标记执行（trader 角色）。APPROVED → EXECUTED。"""
    mod = await get_modification_or_404(db, auction_id, mid)
    transition_mod_status(mod.status, "EXECUTED")

    now = datetime.now(timezone.utc)
    mod.status = "EXECUTED"
    mod.executed_by = current_user.id
    mod.executed_at = now
    mod.execution_result = body.execution_result
    mod.updated_at = now

    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{auction_id}/modifications/{mid}/post-explanation
# ---------------------------------------------------------------------------


@router.post("/{mid}/post-explanation", response_model=dict)
async def post_explanation(
    auction_id: UUID,
    mid: UUID,
    body: PostExplanationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader", "retrospective_owner")),
) -> dict:
    """补充应急说明（trader/retrospective_owner 角色）。
    PENDING_POST_EXPLANATION → POST_EXPLAINED
    PENDING_DEVIATION_EXPLANATION → POST_EXPLAINED
    """
    mod = await get_modification_or_404(db, auction_id, mid)
    transition_mod_status(mod.status, "POST_EXPLAINED")

    now = datetime.now(timezone.utc)
    mod.status = "POST_EXPLAINED"
    mod.post_explanation = body.post_explanation
    mod.deviation_reason = body.deviation_reason
    mod.updated_at = now

    await db.flush()
    await db.refresh(mod)
    return ok(data=ModificationResponse.model_validate(mod).model_dump())
