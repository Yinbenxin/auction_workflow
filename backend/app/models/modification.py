from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

TIMESTAMPTZ = TIMESTAMP(timezone=True)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Modification(Base):
    """临场修改申请表，记录竞拍执行过程中的修改申请及其审批状态。"""

    __tablename__ = "modifications"

    # --- 主键 ---
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # --- 关联竞拍 ---
    auction_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- 关联策略版本 ---
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("strategy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- 状态 ---
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'DRAFT'"),
    )

    # --- 修改内容 ---
    affected_fields: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    before_value: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    after_value: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # --- 必填说明 ---
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    impact_scope: Mapped[str] = mapped_column(Text, nullable=False)
    risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 应急标记 ---
    is_emergency: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_pre_authorized: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    matched_emergency_rule_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    deviation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 附件 ---
    attachments: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    # --- 申请人 ---
    requested_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        server_default=text("now()"),
    )

    # --- 审批字段 ---
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    approval_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 复核字段 ---
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 执行字段 ---
    executed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    execution_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 审计字段 ---
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        server_default=text("now()"),
    )

    # --- 关系 ---
    requested_by_user: Mapped[User] = relationship(
        "User",
        foreign_keys=[requested_by],
        lazy="select",
    )
    approved_by_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[approved_by],
        lazy="select",
    )
    reviewed_by_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reviewed_by],
        lazy="select",
    )
    executed_by_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[executed_by],
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Modification id={self.id!s} auction_id={self.auction_id!s} "
            f"status={self.status!r} is_emergency={self.is_emergency}>"
        )
