from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Decode JWT, verify it, and return the current user record.
    Raises HTTP 401 if the token is invalid or the user does not exist.
    The User model import is deferred to avoid circular imports at bootstrap time;
    replace the stub below once app.models.user is implemented.
    """
    payload = verify_token(token)
    user_id_str: str | None = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 缺少 user_id 字段",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from uuid import UUID as _UUID

    try:
        user_id = _UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中 user_id 格式无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Deferred import — avoids circular dependency before models are defined
    from app.models import User  # noqa: PLC0415  (will exist after T1)

    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str) -> Callable:
    """
    Factory that returns a FastAPI dependency enforcing role membership.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            current_user = Depends(require_role("admin", "super_admin"))
        ):
            ...
    """

    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色：{', '.join(roles)}",
            )
        return current_user

    return role_checker
