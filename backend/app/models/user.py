import enum
import uuid

from sqlalchemy import Boolean, Enum as SAEnum, String, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.core.database import Base


class SystemRole(str, enum.Enum):
    root = "root"
    user = "user"


VALID_ROLES = {
    "business_owner",
    "strategy_owner",
    "auditor",
    "trader",
    "reviewer",
    "data_analyst",
    "monitor",
    "retrospective_owner",
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    system_role: Mapped[SystemRole] = mapped_column(
        SAEnum(SystemRole, name="system_role_enum"),
        nullable=False,
        server_default="user",
    )
    user_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'::text[]"),
    )
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
