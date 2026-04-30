from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.auction import Auction
from app.models.confirmation import Confirmation
from app.schemas.auction import (
    AuctionCreate,
    AuctionUpdate,
    AuctionResponse,
    BasicInfoUpdate,
    HistoryAnalysisUpdate,
    StrategyDataUpdate,
    StrategyApprovalRequest,
)
from app.services.strategy_service import update_with_optimistic_lock

router = APIRouter()

# ---------------------------------------------------------------------------
# 阶段门控
# ---------------------------------------------------------------------------

PHASE_GATES: dict[int, object] = {
    2: lambda a: a.phase_statuses.get("1") == "confirmed",
    3: lambda a: True,  # 软阻断，允许继续
    4: lambda a: a.phase_statuses.get("3") == "has_final_strategy",
    5: lambda a: a.phase_statuses.get("4") == "passed",
    8: lambda a: a.phase_statuses.get("7") == "completed",
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
    current_user=Depends(get_current_user),
) -> dict:
    """创建竞拍项目（任意登录用户）。角色在创建时由表单指定。"""
    auction = Auction(
        name=body.name,
        auction_date=body.auction_date,
        description=body.description,
        current_phase=1,
        phase_statuses={},
        basic_info={},
        history_analysis={},
        roles=body.roles,
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
# PUT /auctions/{id} — 修改竞拍项目基本信息
# ---------------------------------------------------------------------------


@router.put("/{auction_id}", response_model=dict)
async def update_auction(
    auction_id: UUID,
    body: AuctionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """修改竞拍项目名称、竞拍日期、角色分配（任意登录用户）。"""
    auction = await get_auction_or_404(db, auction_id)
    if body.name is not None:
        auction.name = body.name
    if body.auction_date is not None:
        auction.auction_date = body.auction_date
    if body.description is not None:
        auction.description = body.description
    if body.roles is not None:
        auction.roles = body.roles
    auction.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# DELETE /auctions/{id} — 删除竞拍项目
# ---------------------------------------------------------------------------


@router.delete("/{auction_id}", response_model=dict)
async def delete_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """删除竞拍项目（任意登录用户）。"""
    auction = await get_auction_or_404(db, auction_id)
    await db.delete(auction)
    await db.flush()
    return ok(data={"id": str(auction_id)})


# ---------------------------------------------------------------------------
# PUT /auctions/{id}/basic-info — 更新阶段01基础信息
# ---------------------------------------------------------------------------


@router.put("/{auction_id}/basic-info", response_model=dict)
async def update_basic_info(
    auction_id: UUID,
    body: BasicInfoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """更新阶段01基础信息（business_owner 角色），使用乐观锁。确认后仍可修改，状态回退为 in_progress。"""
    auction = await get_auction_or_404(db, auction_id)
    # 角色校验
    if str((auction.roles or {}).get("business_owner")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 business_owner 可修改基础信息")

    update_dict: dict = {"basic_info": body.basic_info, "updated_at": datetime.utcnow()}
    phase_statuses = dict(auction.phase_statuses or {})
    if phase_statuses.get("1") == "confirmed":
        phase_statuses["1"] = "in_progress"
        update_dict["phase_statuses"] = phase_statuses

    await update_with_optimistic_lock(db, Auction, auction_id, body.version, update_dict)
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
    new_phase = max(auction.current_phase, 2)
    await update_with_optimistic_lock(
        db,
        Auction,
        auction_id,
        auction.version,
        {
            "phase_statuses": new_statuses,
            "current_phase": new_phase,
            "updated_at": datetime.utcnow(),
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
    current_user=Depends(get_current_user),
) -> dict:
    """更新阶段02历史分析数据（strategy_owner 角色）。确认后仍可修改，状态回退为 in_progress。"""
    auction = await get_auction_or_404(db, auction_id)
    check_phase_gate(auction, 2)
    # 角色校验：strategy_owner 或 data_analyst 均可编辑
    roles = auction.roles or {}
    allowed = {str(roles.get("strategy_owner")), str(roles.get("data_analyst"))}
    if str(current_user.id) not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 strategy_owner 或 data_analyst 可修改历史分析")

    update_dict: dict = {"history_analysis": body.history_analysis, "updated_at": datetime.utcnow()}
    phase_statuses = dict(auction.phase_statuses or {})
    if phase_statuses.get("2") == "confirmed":
        phase_statuses["2"] = "in_progress"
        update_dict["phase_statuses"] = phase_statuses

    await update_with_optimistic_lock(db, Auction, auction_id, body.version, update_dict)
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
    new_phase = max(auction.current_phase, 3)
    await update_with_optimistic_lock(
        db,
        Auction,
        auction_id,
        auction.version,
        {
            "phase_statuses": new_statuses,
            "current_phase": new_phase,
            "updated_at": datetime.utcnow(),
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


# ---------------------------------------------------------------------------
# 文件上传辅助
# ---------------------------------------------------------------------------

UPLOAD_BASE = Path("uploads")


def _save_upload(subdir: str, auction_id: UUID, file_bytes: bytes, filename: str) -> dict:
    upload_dir = UPLOAD_BASE / subdir / str(auction_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid4())
    suffix = Path(filename).suffix.lower() or ".pdf"
    dest = upload_dir / f"{file_id}{suffix}"
    dest.write_bytes(file_bytes)
    return {
        "id": file_id,
        "filename": filename,
        "size": len(file_bytes),
        "url": f"/uploads/{subdir}/{auction_id}/{file_id}{suffix}",
        "uploaded_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /auctions/{id}/basic-info/upload — 上传阶段01附件
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/basic-info/upload", response_model=dict)
async def upload_basic_info_attachment(
    auction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """上传阶段01附件（仅限 PDF）。返回附件元数据，前端负责将其追加到 basic_info.attachments 并保存。"""
    auction = await get_auction_or_404(db, auction_id)
    if str((auction.roles or {}).get("business_owner")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 business_owner 可上传附件")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": 400, "data": None, "message": "仅支持 PDF 文件"})
    content = await file.read()
    meta = _save_upload("basic_info", auction_id, content, file.filename or "attachment.pdf")
    return ok(data=meta)


# ---------------------------------------------------------------------------
# DELETE /auctions/{id}/basic-info/attachment/{file_id} — 删除阶段01附件
# ---------------------------------------------------------------------------


@router.delete("/{auction_id}/basic-info/attachment/{file_id}", response_model=dict)
async def delete_basic_info_attachment(
    auction_id: UUID,
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """删除阶段01附件文件（仅限 business_owner）。"""
    auction = await get_auction_or_404(db, auction_id)
    if str((auction.roles or {}).get("business_owner")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 business_owner 可删除附件")
    upload_dir = UPLOAD_BASE / "basic_info" / str(auction_id)
    for f in upload_dir.glob(f"{file_id}*") if upload_dir.exists() else []:
        f.unlink(missing_ok=True)
    return ok(data={"file_id": file_id})


# ---------------------------------------------------------------------------
# POST /auctions/{id}/history-analysis/upload — 上传阶段02附件
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/history-analysis/upload", response_model=dict)
async def upload_history_analysis_attachment(
    auction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """上传阶段02附件（仅限 PDF）。"""
    auction = await get_auction_or_404(db, auction_id)
    roles = auction.roles or {}
    allowed = {str(roles.get("strategy_owner")), str(roles.get("data_analyst"))}
    if str(current_user.id) not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 strategy_owner 或 data_analyst 可上传附件")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": 400, "data": None, "message": "仅支持 PDF 文件"})
    content = await file.read()
    meta = _save_upload("history_analysis", auction_id, content, file.filename or "attachment.pdf")
    return ok(data=meta)


# ---------------------------------------------------------------------------
# DELETE /auctions/{id}/history-analysis/attachment/{file_id} — 删除阶段02附件
# ---------------------------------------------------------------------------


@router.delete("/{auction_id}/history-analysis/attachment/{file_id}", response_model=dict)
async def delete_history_analysis_attachment(
    auction_id: UUID,
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """删除阶段02附件文件。"""
    auction = await get_auction_or_404(db, auction_id)
    roles = auction.roles or {}
    allowed = {str(roles.get("strategy_owner")), str(roles.get("data_analyst"))}
    if str(current_user.id) not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 strategy_owner 或 data_analyst 可删除附件")
    upload_dir = UPLOAD_BASE / "history_analysis" / str(auction_id)
    for f in upload_dir.glob(f"{file_id}*") if upload_dir.exists() else []:
        f.unlink(missing_ok=True)
    return ok(data={"file_id": file_id})


# ---------------------------------------------------------------------------
# PUT /auctions/{id}/strategy — 更新阶段03策略内容
# ---------------------------------------------------------------------------


@router.put("/{auction_id}/strategy", response_model=dict)
async def update_strategy(
    auction_id: UUID,
    body: StrategyDataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """更新阶段03策略内容（strategy_owner 角色）。确认后仍可修改，状态回退为 in_progress。"""
    auction = await get_auction_or_404(db, auction_id)
    if str((auction.roles or {}).get("strategy_owner")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 strategy_owner 可修改策略内容")

    update_dict: dict = {"strategy_data": body.strategy_data, "updated_at": datetime.utcnow()}
    phase_statuses = dict(auction.phase_statuses or {})
    if phase_statuses.get("3") in ("confirmed", "rejected"):
        phase_statuses["3"] = "in_progress"
        update_dict["phase_statuses"] = phase_statuses

    await update_with_optimistic_lock(db, Auction, auction_id, body.version, update_dict)
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# ---------------------------------------------------------------------------
# POST /auctions/{id}/strategy/confirm — 确认阶段03策略
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/strategy/confirm", response_model=dict)
async def confirm_strategy(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """确认阶段03策略（strategy_owner 角色）。更新 phase_statuses["3"]="confirmed"，写入确认记录。"""
    auction = await get_auction_or_404(db, auction_id)
    if str((auction.roles or {}).get("strategy_owner")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 strategy_owner 可确认策略")

    new_statuses = {**auction.phase_statuses, "3": "confirmed"}
    new_phase = max(auction.current_phase, 4)
    await update_with_optimistic_lock(
        db, Auction, auction_id, auction.version,
        {"phase_statuses": new_statuses, "current_phase": new_phase, "updated_at": datetime.utcnow()},
    )

    confirmation = Confirmation(
        target_type="strategy_data",
        target_id=auction_id,
        action="confirm",
        confirmed_by=current_user.id,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# POST /auctions/{id}/strategy/approve — 审批通过阶段03策略
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/strategy/approve", response_model=dict)
async def approve_strategy(
    auction_id: UUID,
    body: StrategyApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """审批通过阶段03策略（auditor 角色）。更新 phase_statuses["3"]="has_final_strategy"。"""
    auction = await get_auction_or_404(db, auction_id)
    if str((auction.roles or {}).get("auditor")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 auditor 可审批策略")
    if auction.phase_statuses.get("3") != "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="策略尚未确认，无法审批")

    new_statuses = {**auction.phase_statuses, "3": "has_final_strategy"}
    new_phase = max(auction.current_phase, 4)
    await update_with_optimistic_lock(
        db, Auction, auction_id, auction.version,
        {"phase_statuses": new_statuses, "current_phase": new_phase, "updated_at": datetime.utcnow()},
    )

    confirmation = Confirmation(
        target_type="strategy_approval",
        target_id=auction_id,
        action="approve",
        confirmed_by=current_user.id,
        comment=body.comment,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())


# POST /auctions/{id}/strategy/reject — 审批驳回阶段03策略
# ---------------------------------------------------------------------------


@router.post("/{auction_id}/strategy/reject", response_model=dict)
async def reject_strategy(
    auction_id: UUID,
    body: StrategyApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """审批驳回阶段03策略（auditor 角色）。更新 phase_statuses["3"]="rejected"，保留驳回意见在 "3_comment"。"""
    auction = await get_auction_or_404(db, auction_id)
    if str((auction.roles or {}).get("auditor")) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 auditor 可审批策略")
    if auction.phase_statuses.get("3") != "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="策略尚未确认，无法审批")

    new_statuses = {**auction.phase_statuses, "3": "rejected", "3_comment": body.comment or ""}
    await update_with_optimistic_lock(
        db, Auction, auction_id, auction.version,
        {"phase_statuses": new_statuses, "updated_at": datetime.utcnow()},
    )

    confirmation = Confirmation(
        target_type="strategy_approval",
        target_id=auction_id,
        action="reject",
        confirmed_by=current_user.id,
        comment=body.comment,
    )
    db.add(confirmation)
    await db.flush()
    await db.refresh(auction)
    return ok(data=AuctionResponse.model_validate(auction).model_dump())
