from typing import Callable
from uuid import UUID as _UUID

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
    payload = verify_token(token)
    user_id_str: str | None = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 缺少 user_id 字段",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = _UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中 user_id 格式无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.models import User  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_auction_role(*roles: str) -> Callable:
    """
    Factory that returns a FastAPI dependency enforcing that the current user
    holds one of the given roles in the auction identified by `auction_id`
    path parameter.

    The auction's `roles` JSONB field maps role names to user UUIDs (as strings).
    Usage:
        @router.post("/{auction_id}/basic-info/confirm")
        async def confirm(
            auction_id: UUID,
            current_user=Depends(require_auction_role("business_owner")),
            db: AsyncSession = Depends(get_db),
        ):
    """

    async def role_checker(
        auction_id: _UUID,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from app.models.auction import Auction  # noqa: PLC0415
        from sqlalchemy import select  # noqa: PLC0415

        result = await db.execute(select(Auction).where(Auction.id == auction_id))
        auction = result.scalar_one_or_none()
        if auction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="竞拍项目不存在",
            )

        auction_roles: dict = auction.roles or {}
        user_id_str = str(current_user.id)
        for role in roles:
            if auction_roles.get(role) == user_id_str:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足，需要角色：{', '.join(roles)}",
        )

    return role_checker


# Keep old name as alias so existing imports don't break immediately
def require_role(*roles: str) -> Callable:
    """Deprecated: use require_auction_role. Kept for backward compatibility."""
    return require_auction_role(*roles)
