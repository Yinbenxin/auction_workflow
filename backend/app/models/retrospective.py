from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.auction import Auction
    from app.models.strategy import StrategyVersion


class Retrospective(Base):
    """复盘报告表，记录竞拍结束后的复盘分析与归档信息。"""

    __tablename__ = "retrospectives"

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
    )

    # --- JSONB 结构化字段 ---
    basic_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    strategy_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    execution_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    transaction_result: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # --- 文本分析字段（可空） ---
    deviation_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    anomaly_records: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_records: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_learnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 状态 ---
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
    )

    # --- 审计字段 ---
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # --- 关系 ---
    created_by_user: Mapped[User] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Retrospective id={self.id!s} auction_id={self.auction_id!s} "
            f"status={self.status!r}>"
        )
