from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.auction import Auction


class StrategyVersion(Base):
    """策略版本表，记录每个竞拍的策略方案及其审批状态。"""

    __tablename__ = "strategy_versions"
    __table_args__ = (
        UniqueConstraint("auction_id", "version_code", name="uq_strategy_auction_version_code"),
    )

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

    # --- 版本标识 ---
    version_code: Mapped[str] = mapped_column(String(50), nullable=False)
    version_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # --- 状态 ---
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'DRAFT'"),
    )

    # --- 核心竞拍参数（红线字段） ---
    bid_price: Mapped[Any] = mapped_column(Numeric(18, 4), nullable=True)
    bid_quantity: Mapped[Any] = mapped_column(Numeric(18, 2), nullable=True)
    bid_time_points: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    trigger_conditions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    fallback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    applicable_scenarios: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    # --- 场景策略 ---
    scenario_strategies: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # --- 风险管理 ---
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'NORMAL'"),
    )
    pre_authorized_actions: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 版本溯源（自引用） ---
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("strategy_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- 乐观锁 ---
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    # --- 审计字段 ---
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )

    # --- 关系 ---
    created_by_user: Mapped[User] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="select",
    )
    previous_version: Mapped[StrategyVersion | None] = relationship(
        "StrategyVersion",
        foreign_keys=[previous_version_id],
        remote_side="StrategyVersion.id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<StrategyVersion id={self.id!s} code={self.version_code!r} "
            f"status={self.status!r} version={self.version}>"
        )
