from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MonitorRecordCreate(BaseModel):
    record_type: str = "normal"  # normal / anomaly
    price_change: Optional[Decimal] = None
    remaining_quantity: Optional[Decimal] = None
    transaction_speed: Optional[str] = None
    data_feed_normal: bool = True
    system_normal: bool = True
    anomaly_type: Optional[str] = None
    anomaly_action: Optional[str] = None


class MonitorRecordResponse(BaseModel):
    id: UUID
    auction_id: UUID
    record_type: str
    price_change: Optional[Decimal]
    remaining_quantity: Optional[Decimal]
    transaction_speed: Optional[str]
    data_feed_normal: bool
    system_normal: bool
    anomaly_type: Optional[str]
    anomaly_action: Optional[str]
    recorded_by: UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
