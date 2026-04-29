from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.auction import Auction
from app.models.task_config import TaskConfig
from app.schemas.task_config import TaskConfigResponse, TaskConfigUpdate

router = APIRouter()


@router.get("/{auction_id}/task-config", response_model=dict)
async def get_task_config(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取指定竞拍的任务配置，不存在返回 404。"""
    result = await db.execute(
        select(TaskConfig).where(TaskConfig.auction_id == auction_id)
    )
    task_config: TaskConfig | None = result.scalar_one_or_none()

    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "任务配置不存在"},
        )

    return ok(data=TaskConfigResponse.model_validate(task_config).model_dump())


@router.put("/{auction_id}/task-config", response_model=dict)
async def upsert_task_config(
    auction_id: UUID,
    body: TaskConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """更新任务配置（trader 角色）。不存在则创建，存在则更新（status 必须为 pending）。"""
    result = await db.execute(
        select(TaskConfig).where(TaskConfig.auction_id == auction_id)
    )
    task_config: TaskConfig | None = result.scalar_one_or_none()

    if task_config is None:
        # 创建新记录
        task_config = TaskConfig(
            auction_id=auction_id,
            strategy_version_id=body.strategy_version_id,
            tasks=body.tasks,
            attachments=body.attachments,
            configured_by=current_user.id,
        )
        db.add(task_config)
    else:
        if task_config.status == "confirmed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 400, "data": None, "message": "任务配置已确认，不可修改"},
            )
        task_config.strategy_version_id = body.strategy_version_id
        task_config.tasks = body.tasks
        task_config.attachments = body.attachments

    await db.flush()
    await db.refresh(task_config)
    return ok(data=TaskConfigResponse.model_validate(task_config).model_dump())


@router.post("/{auction_id}/task-config/confirm", response_model=dict)
async def confirm_task_config(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """确认任务配置完成（trader 角色），将 status 改为 confirmed 并更新 auction.phase_statuses["5"]。"""
    # 获取任务配置
    tc_result = await db.execute(
        select(TaskConfig).where(TaskConfig.auction_id == auction_id)
    )
    task_config: TaskConfig | None = tc_result.scalar_one_or_none()

    if task_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "任务配置不存在"},
        )

    if task_config.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "任务配置已确认，不可重复确认"},
        )

    # 更新任务配置状态
    task_config.status = "confirmed"

    # 更新 auction.phase_statuses["5"]
    auction_result = await db.execute(
        select(Auction).where(Auction.id == auction_id)
    )
    auction: Auction | None = auction_result.scalar_one_or_none()
    if auction is not None:
        updated_statuses = dict(auction.phase_statuses or {})
        updated_statuses["5"] = "confirmed"
        auction.phase_statuses = updated_statuses

    await db.flush()
    await db.refresh(task_config)
    return ok(data=TaskConfigResponse.model_validate(task_config).model_dump())
