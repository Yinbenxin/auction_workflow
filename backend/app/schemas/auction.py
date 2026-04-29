from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuctionCreate(BaseModel):
    name: str
    auction_date: date


class AuctionUpdate(BaseModel):
    name: Optional[str] = None
    auction_date: Optional[date] = None


class BasicInfoUpdate(BaseModel):
    basic_info: dict
    version: int  # 乐观锁


class HistoryAnalysisUpdate(BaseModel):
    history_analysis: dict
    version: int  # 乐观锁


class AuctionResponse(BaseModel):
    id: UUID
    name: str
    auction_date: date
    current_phase: int
    phase_statuses: dict[str, Any]
    basic_info: dict[str, Any]
    history_analysis: dict[str, Any]
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
