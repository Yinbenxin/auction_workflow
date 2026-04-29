from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserResponse


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


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return ok(data=UserResponse.model_validate(current_user).model_dump())
