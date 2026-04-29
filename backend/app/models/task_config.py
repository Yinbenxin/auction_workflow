from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class TaskConfig(Base):
    """任务配置表，记录竞拍阶段5（任务配置）的具体任务列表和附件。"""

    __tablename__ = "task_configs"

    # --- 主键 ---
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # --- 外键 ---
    auction_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("strategy_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    configured_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # --- 业务数据 ---
    # 每项含：任务编号/任务时间/价格/数量/触发条件/任务顺序/启停状态/垫子策略/补量策略/兜底任务标识
    tasks: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    # 配置截图或导出文件
    attachments: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    # --- 状态 ---
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )

    # --- 审计字段 ---
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # --- 关系 ---
    configured_by_user: Mapped[User] = relationship(
        "User",
        foreign_keys=[configured_by],
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<TaskConfig id={self.id!s} auction_id={self.auction_id!s} "
            f"status={self.status!r}>"
        )
