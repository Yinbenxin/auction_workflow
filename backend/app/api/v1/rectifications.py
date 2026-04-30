from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import ok
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.rectification import RectificationItem
from app.schemas.rectification import (
    ConfirmRequest,
    RectificationCreate,
    RectificationResponse,
    RectificationUpdate,
)

# retrospectives-scoped routes: /retrospectives/{rid}/rectification-items
retrospectives_router = APIRouter()

# item-scoped routes: /rectification-items/{iid}/...
items_router = APIRouter()


async def _get_retrospective_or_404(retrospective_id: UUID, db: AsyncSession) -> None:
    """验证复盘报告存在，不存在则抛 404。"""
    from app.models.retrospective import Retrospective  # noqa: PLC0415

    result = await db.execute(
        select(Retrospective).where(Retrospective.id == retrospective_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "复盘报告不存在"},
        )


async def _get_item_or_404(item_id: UUID, db: AsyncSession) -> RectificationItem:
    """获取整改事项，不存在则抛 404。"""
    result = await db.execute(
        select(RectificationItem).where(RectificationItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "整改事项不存在"},
        )
    return item


# ---------------------------------------------------------------------------
# POST /retrospectives/{rid}/rectification-items — 创建整改事项
# ---------------------------------------------------------------------------

@retrospectives_router.post("/{rid}/rectification-items", response_model=dict)
async def create_rectification_item(
    rid: UUID,
    body: RectificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """创建整改事项（该竞拍的 retrospective_owner 角色）。measures 和 due_date 必填。"""
    await _get_retrospective_or_404(rid, db)

    # 权限校验：只有该竞拍的 retrospective_owner 可创建整改事项
    from app.models.retrospective import Retrospective  # noqa: PLC0415
    from app.models.auction import Auction  # noqa: PLC0415
    retro_result = await db.execute(select(Retrospective).where(Retrospective.id == rid))
    retro = retro_result.scalar_one_or_none()
    has_permission = False
    if retro:
        auction_result = await db.execute(select(Auction).where(Auction.id == retro.auction_id))
        auction = auction_result.scalar_one_or_none()
        if auction:
            has_permission = (auction.roles or {}).get("retrospective_owner") == str(current_user.id)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "data": None, "message": "只有复盘负责人可创建整改事项"},
        )

    item = RectificationItem(
        retrospective_id=rid,
        title=body.title,
        description=body.description,
        assignee_id=body.assignee_id,
        measures=body.measures,
        due_date=body.due_date,
        status="OPEN",
        evidence=[],
        created_by=current_user.id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return ok(data=RectificationResponse.model_validate(item).model_dump())


# ---------------------------------------------------------------------------
# GET /retrospectives/{rid}/rectification-items — 查询整改事项列表
# ---------------------------------------------------------------------------

@retrospectives_router.get("/{rid}/rectification-items", response_model=dict)
async def list_rectification_items(
    rid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """查询复盘报告下的整改事项列表，按 created_at ASC 排序。"""
    await _get_retrospective_or_404(rid, db)

    result = await db.execute(
        select(RectificationItem)
        .where(RectificationItem.retrospective_id == rid)
        .order_by(RectificationItem.created_at.asc())
    )
    items = result.scalars().all()
    data = [RectificationResponse.model_validate(i).model_dump() for i in items]
    return ok(data=data)


# ---------------------------------------------------------------------------
# PUT /rectification-items/{iid} — 更新整改事项
# ---------------------------------------------------------------------------

@items_router.put("/{iid}", response_model=dict)
async def update_rectification_item(
    iid: UUID,
    body: RectificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """更新整改事项（责任人或 retrospective_owner）。
    - status=DELAYED 时 delay_reason 必填
    - status=CLOSED 时 close_reason 必填
    """
    item = await _get_item_or_404(iid, db)

    # 权限校验：只有责任人或该竞拍的 retrospective_owner 可更新
    is_assignee = str(item.assignee_id) == str(current_user.id)
    from app.models.retrospective import Retrospective  # noqa: PLC0415
    from app.models.auction import Auction  # noqa: PLC0415
    retro_result = await db.execute(
        select(Retrospective).where(Retrospective.id == item.retrospective_id)
    )
    retro = retro_result.scalar_one_or_none()
    is_retro_owner = False
    if retro:
        auction_result = await db.execute(
            select(Auction).where(Auction.id == retro.auction_id)
        )
        auction = auction_result.scalar_one_or_none()
        if auction:
            is_retro_owner = (auction.roles or {}).get("retrospective_owner") == str(current_user.id)
    if not is_assignee and not is_retro_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "data": None, "message": "只有责任人或复盘负责人可更新整改事项"},
        )

    # 状态机校验
    if body.status == "DELAYED" and not body.delay_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "状态为 DELAYED 时 delay_reason 必填"},
        )
    if body.status == "CLOSED" and not body.close_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "状态为 CLOSED 时 close_reason 必填"},
        )

    # 应用更新
    if body.title is not None:
        item.title = body.title
    if body.description is not None:
        item.description = body.description
    if body.assignee_id is not None:
        item.assignee_id = body.assignee_id
    if body.measures is not None:
        item.measures = body.measures
    if body.due_date is not None:
        item.due_date = body.due_date
    if body.status is not None:
        item.status = body.status
    if body.delay_reason is not None:
        item.delay_reason = body.delay_reason
    if body.close_reason is not None:
        item.close_reason = body.close_reason

    item.updated_at = datetime.now(tz=timezone.utc)

    await db.flush()
    await db.refresh(item)
    return ok(data=RectificationResponse.model_validate(item).model_dump())


# ---------------------------------------------------------------------------
# POST /rectification-items/{iid}/upload-evidence — 上传完成证据
# ---------------------------------------------------------------------------

@items_router.post("/{iid}/upload-evidence", response_model=dict)
async def upload_evidence(
    iid: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """上传整改完成证据（责任人）。追加到 evidence 列表，不覆盖。"""
    import uuid as _uuid  # noqa: PLC0415

    item = await _get_item_or_404(iid, db)

    # 权限校验：只有责任人可上传证据
    if str(item.assignee_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "data": None, "message": "只有责任人可上传整改证据"},
        )

    # 生成证据记录（实际项目中应存储文件并返回 URL，此处记录文件名作为占位）
    evidence_id = str(_uuid.uuid4())
    evidence_entry = {
        "id": evidence_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "uploaded_by": str(current_user.id),
        "uploaded_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # 追加到 evidence 列表（JSONB 需要重新赋值触发 SQLAlchemy 变更检测）
    current_evidence = list(item.evidence) if item.evidence else []
    current_evidence.append(evidence_entry)
    item.evidence = current_evidence
    item.updated_at = datetime.now(tz=timezone.utc)

    await db.flush()
    await db.refresh(item)
    return ok(data={
        "id": evidence_id,
        "evidence_url": evidence_entry["filename"],
        "file_id": evidence_id,
        "item_id": str(iid),
        "evidence": item.evidence,
    })


# ---------------------------------------------------------------------------
# POST /rectification-items/{iid}/confirm — 确认整改完成或关闭
# ---------------------------------------------------------------------------

@items_router.post("/{iid}/confirm", response_model=dict)
async def confirm_rectification_item(
    iid: UUID,
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """确认整改完成（retrospective_owner 或 business_owner）。
    - 必须有完成证据才能确认
    - 确认后状态变更为 CLOSED，记录 confirmed_by 和 confirmed_at
    """
    item = await _get_item_or_404(iid, db)

    # 权限校验：只有该竞拍的 retrospective_owner 或 business_owner 可确认
    from app.models.retrospective import Retrospective  # noqa: PLC0415
    from app.models.auction import Auction  # noqa: PLC0415
    retro_result = await db.execute(
        select(Retrospective).where(Retrospective.id == item.retrospective_id)
    )
    retro = retro_result.scalar_one_or_none()
    has_permission = False
    if retro:
        auction_result = await db.execute(
            select(Auction).where(Auction.id == retro.auction_id)
        )
        auction = auction_result.scalar_one_or_none()
        if auction:
            auction_roles = auction.roles or {}
            user_id_str = str(current_user.id)
            has_permission = (
                auction_roles.get("retrospective_owner") == user_id_str
                or auction_roles.get("business_owner") == user_id_str
            )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "data": None, "message": "只有复盘负责人或业务负责人可确认整改完成"},
        )

    # 业务校验：必须有完成证据
    if not item.evidence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "data": None,
                "message": "整改事项尚无完成证据（evidence），无法确认完成",
            },
        )

    item.status = "CLOSED"
    item.confirmed_by = current_user.id
    item.confirmed_at = datetime.now(tz=timezone.utc)
    if body.comment:
        item.close_reason = body.comment
    item.updated_at = datetime.now(tz=timezone.utc)

    await db.flush()
    await db.refresh(item)
    return ok(data=RectificationResponse.model_validate(item).model_dump())
