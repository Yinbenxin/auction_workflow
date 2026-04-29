from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.auction import Auction
from app.models.review import PreExecutionReview
from app.schemas.review import (
    ChecklistUpdate,
    PreExecutionReviewResponse,
    ReviewCreate,
    ReviewSubmit,
)
from app.services.review_service import validate_checklist_complete, validate_dual_review

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


async def _get_review_or_404(auction_id: UUID, db: AsyncSession) -> PreExecutionReview:
    result = await db.execute(
        select(PreExecutionReview).where(
            PreExecutionReview.auction_id == auction_id
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "复核记录不存在"},
        )
    return review


@router.get("/{auction_id}/review", response_model=dict)
async def get_review(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取执行前复核记录，不存在返回 404。"""
    await _get_auction_or_404(auction_id, db)
    review = await _get_review_or_404(auction_id, db)
    return ok(data=PreExecutionReviewResponse.model_validate(review).model_dump())


@router.post("/{auction_id}/review", response_model=dict)
async def create_review(
    auction_id: UUID,
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """发起执行前复核（trader 角色），创建 status=pending 的复核记录。"""
    await _get_auction_or_404(auction_id, db)

    # 同一竞拍只允许一条复核记录
    existing = await db.execute(
        select(PreExecutionReview).where(
            PreExecutionReview.auction_id == auction_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "该竞拍已存在复核记录"},
        )

    review = PreExecutionReview(
        auction_id=auction_id,
        strategy_version_id=body.strategy_version_id,
        checklist={},
        status="pending",
        configurer_id=current_user.id,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return ok(data=PreExecutionReviewResponse.model_validate(review).model_dump())


@router.put("/{auction_id}/review/checklist", response_model=dict)
async def update_checklist(
    auction_id: UUID,
    body: ChecklistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("reviewer")),
) -> dict:
    """更新复核清单勾选状态（reviewer 角色）。校验双人复核：复核人不能是配置人。"""
    await _get_auction_or_404(auction_id, db)
    review = await _get_review_or_404(auction_id, db)

    validate_dual_review(review.configurer_id, current_user.id)

    review.checklist = body.checklist
    review.reviewer_id = current_user.id
    await db.flush()
    await db.refresh(review)
    return ok(data=PreExecutionReviewResponse.model_validate(review).model_dump())


@router.post("/{auction_id}/review/submit", response_model=dict)
async def submit_review(
    auction_id: UUID,
    body: ReviewSubmit,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("reviewer")),
) -> dict:
    """提交复核结论（reviewer 角色）。
    - 校验双人复核
    - passed 时必须 13 项全部勾选
    - passed 时更新 auction.phase_statuses["6"] = "passed"
    """
    auction = await _get_auction_or_404(auction_id, db)
    review = await _get_review_or_404(auction_id, db)

    validate_dual_review(review.configurer_id, current_user.id)

    if body.status == "passed" and not validate_checklist_complete(review.checklist):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "data": None,
                "message": "复核结论为 passed 时，13 项清单必须全部勾选",
            },
        )

    review.status = body.status
    review.comment = body.comment
    review.reviewer_id = current_user.id
    review.reviewed_at = datetime.now(tz=timezone.utc)

    if body.status == "passed":
        phase_statuses = dict(auction.phase_statuses)
        phase_statuses["6"] = "passed"
        auction.phase_statuses = phase_statuses

    await db.flush()
    await db.refresh(review)
    return ok(data=PreExecutionReviewResponse.model_validate(review).model_dump())


@router.post("/{auction_id}/mark-executable", response_model=dict)
async def mark_executable(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """标记任务可执行（trader 角色）。
    前置校验：phase_statuses["6"] == "passed"
    通过后更新 phase_statuses["6"] = "executable"
    """
    auction = await _get_auction_or_404(auction_id, db)

    if auction.phase_statuses.get("6") != "passed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "data": None,
                "message": "执行前复核尚未通过，无法标记为可执行",
            },
        )

    phase_statuses = dict(auction.phase_statuses)
    phase_statuses["6"] = "executable"
    auction.phase_statuses = phase_statuses

    await db.flush()
    return ok(data={"auction_id": str(auction_id), "phase_6_status": "executable"})
