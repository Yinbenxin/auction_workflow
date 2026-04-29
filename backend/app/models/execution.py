from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.core.database import Base


class ExecutionLog(Base):
    """竞拍执行日志，记录正式竞拍阶段每个任务节点的执行情况。"""

    __tablename__ = "execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auctions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    task_number: Mapped[str] = mapped_column(String(50), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    bid_price: Mapped[float | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )
    bid_quantity: Mapped[float | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    system_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_feed_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutionLog id={self.id!s} auction_id={self.auction_id!s} "
            f"task_number={self.task_number!r} triggered_at={self.triggered_at}>"
        )
