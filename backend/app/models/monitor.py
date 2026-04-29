import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.core.database import Base


class MonitorRecord(Base):
    __tablename__ = "monitor_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auctions.id"),
        nullable=False,
    )
    record_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'normal'"),
    )
    price_change: Mapped[object] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )
    remaining_quantity: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    transaction_speed: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    data_feed_normal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    system_normal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    anomaly_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    anomaly_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    recorded_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
