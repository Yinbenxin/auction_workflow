from uuid import UUID, uuid4
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.auction import Auction
from app.models.confirmation import Confirmation
from app.models.task_config import TaskConfig
from app.schemas.task_config import TaskConfigApprovalRequest, TaskConfigResponse, TaskConfigUpdate

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
        task_config.strategy_version_id = body.strategy_version_id
        task_config.tasks = body.tasks
        task_config.attachments = body.attachments
        # 若已确认或已驳回，保存时自动回退为 pending
        if task_config.status in ("confirmed", "rejected"):
            task_config.status = "pending"
        # 同步回退 phase_statuses["4"]
        auction_result2 = await db.execute(select(Auction).where(Auction.id == auction_id))
        auction2: Auction | None = auction_result2.scalar_one_or_none()
        if auction2 and (auction2.phase_statuses or {}).get("4") in ("confirmed", "rejected"):
            updated = dict(auction2.phase_statuses)
            updated["4"] = "in_progress"
            auction2.phase_statuses = updated

    await db.flush()
    await db.refresh(task_config)
    return ok(data=TaskConfigResponse.model_validate(task_config).model_dump())


@router.post("/{auction_id}/task-config/confirm", response_model=dict)
async def confirm_task_config(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("trader")),
) -> dict:
    """确认任务配置完成（trader 角色），将 status 改为 confirmed 并更新 auction.phase_statuses["4"]。"""
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

    # 更新 auction.phase_statuses["4"]
    auction_result = await db.execute(
        select(Auction).where(Auction.id == auction_id)
    )
    auction: Auction | None = auction_result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(status_code=404, detail="竞拍项目不存在")
    updated_statuses = dict(auction.phase_statuses or {})
    updated_statuses["4"] = "confirmed"
    auction.phase_statuses = updated_statuses
    await db.flush()
    await db.refresh(task_config)
    return ok(data=TaskConfigResponse.model_validate(task_config).model_dump())


@router.post("/{auction_id}/task-config/attachments", response_model=dict)
async def upload_task_config_attachment(
    auction_id: UUID,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
) -> dict:
    """上传任务配置附件，返回文件元数据。"""
    upload_dir = Path("uploads/task_config") / str(auction_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid4())
    suffix = Path(file.filename or "file.pdf").suffix
    dest = upload_dir / f"{file_id}{suffix}"
    dest.write_bytes(await file.read())
    return ok(data={
        "id": file_id,
        "filename": file.filename,
        "size": dest.stat().st_size,
        "url": f"/uploads/task_config/{auction_id}/{file_id}{suffix}",
        "uploaded_at": datetime.utcnow().isoformat(),
    })


@router.post("/{auction_id}/task-config/approve", response_model=dict)
async def approve_task_config(
    auction_id: UUID,
    body: TaskConfigApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """审批通过任务配置（reviewer 角色）。更新 phase_statuses["4"]="passed"。"""
    auction_result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction: Auction | None = auction_result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(status_code=404, detail="竞拍项目不存在")
    if str((auction.roles or {}).get("reviewer")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 reviewer 可审批任务配置")
    if (auction.phase_statuses or {}).get("4") != "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务配置尚未确认，无法审批")

    new_statuses = {**auction.phase_statuses, "4": "passed"}
    auction.phase_statuses = new_statuses
    auction.current_phase = max(auction.current_phase, 5)

    confirmation = Confirmation(
        target_type="task_config_approval",
        target_id=auction_id,
        action="approve",
        confirmed_by=current_user.id,
        comment=body.comment,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    from app.schemas.auction import AuctionResponse
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


@router.post("/{auction_id}/task-config/reject", response_model=dict)
async def reject_task_config(
    auction_id: UUID,
    body: TaskConfigApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """审批驳回任务配置（reviewer 角色）。回退 phase_statuses["4"]="rejected"，task_config.status="pending"。"""
    auction_result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction: Auction | None = auction_result.scalar_one_or_none()
    if auction is None:
        raise HTTPException(status_code=404, detail="竞拍项目不存在")
    if str((auction.roles or {}).get("reviewer")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 reviewer 可审批任务配置")
    if (auction.phase_statuses or {}).get("4") != "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务配置尚未确认，无法审批")

    new_statuses = {
        **auction.phase_statuses,
        "4": "rejected",
        "4_comment": body.comment or "",
    }
    auction.phase_statuses = new_statuses

    # 同时回退 task_config.status
    tc_result = await db.execute(select(TaskConfig).where(TaskConfig.auction_id == auction_id))
    task_config: TaskConfig | None = tc_result.scalar_one_or_none()
    if task_config is not None:
        task_config.status = "pending"

    confirmation = Confirmation(
        target_type="task_config_approval",
        target_id=auction_id,
        action="reject",
        confirmed_by=current_user.id,
        comment=body.comment,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    from app.schemas.auction import AuctionResponse
    return ok(data=AuctionResponse.model_validate(auction).model_dump())
