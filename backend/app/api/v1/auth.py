from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.dependencies import get_current_user, require_root
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse, UserAdminCreate, UserAdminUpdate


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


router = APIRouter()


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == body.username))
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "用户名或密码错误"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "账号已禁用"},
        )

    access_token = create_access_token({"user_id": str(user.id)})
    token_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
    return ok(data=token_data.model_dump())


@router.post("/register")
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "用户名已存在"},
        )

    user = User(
        username=body.username,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return ok(data=UserResponse.model_validate(user).model_dump())


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return ok(data=UserResponse.model_validate(current_user).model_dump())


@router.put("/me/password")
async def change_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "原密码错误"},
        )
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "新密码至少6位"},
        )
    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    return ok(data=None, message="密码修改成功")


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """列出所有活跃用户（用于角色分配选择器）。"""
    result = await db.execute(
        select(User).where(User.is_active == True).order_by(User.full_name)  # noqa: E712
    )
    users = result.scalars().all()
    return ok(data=[UserResponse.model_validate(u).model_dump() for u in users])


@router.get("/admin/users")
async def admin_list_users(
    db: AsyncSession = Depends(get_db),
    _root: User = Depends(require_root),
):
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return ok(data=[UserResponse.model_validate(u).model_dump() for u in users])


@router.post("/admin/users")
async def admin_create_user(
    body: UserAdminCreate,
    db: AsyncSession = Depends(get_db),
    _root: User = Depends(require_root),
):
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "用户名已存在"},
        )
    user = User(
        username=body.username,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        system_role=body.system_role,
        user_roles=body.user_roles,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return ok(data=UserResponse.model_validate(user).model_dump())


@router.put("/admin/users/{user_id}")
async def admin_update_user(
    user_id: UUID,
    body: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    root: User = Depends(require_root),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "用户不存在"},
        )
    if target.id == root.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "不能修改自身账号"},
        )
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.system_role is not None:
        target.system_role = body.system_role
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.user_roles is not None:
        target.user_roles = body.user_roles
    await db.commit()
    await db.refresh(target)
    return ok(data=UserResponse.model_validate(target).model_dump())


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    root: User = Depends(require_root),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "data": None, "message": "用户不存在"},
        )
    if target.id == root.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "data": None, "message": "不能删除自身账号"},
        )
    await db.delete(target)
    await db.commit()
    return ok(data=None, message="用户已删除")