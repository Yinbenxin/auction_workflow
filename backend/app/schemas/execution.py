from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExecutionLogCreate(BaseModel):
    task_number: str
    triggered_at: datetime
    bid_price: Optional[Decimal] = None
    bid_quantity: Optional[Decimal] = None
    system_status: Optional[str] = None
    data_feed_status: Optional[str] = None
    result: Optional[str] = None
    notes: Optional[str] = None


class ExecutionLogResponse(BaseModel):
    id: UUID
    auction_id: UUID
    task_number: str
    triggered_at: datetime
    bid_price: Optional[Decimal]
    bid_quantity: Optional[Decimal]
    system_status: Optional[str]
    data_feed_status: Optional[str]
    result: Optional[str]
    notes: Optional[str]
    logged_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
