from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    full_name: str
    is_active: bool
    system_role: str
    user_roles: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserAdminCreate(BaseModel):
    username: str
    password: str
    full_name: str
    system_role: str = "user"
    user_roles: list[str] = []


class UserAdminUpdate(BaseModel):
    full_name: str | None = None
    system_role: str | None = None
    is_active: bool | None = None
    user_roles: list[str] | None = None
