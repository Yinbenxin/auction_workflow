from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrategyCreate(BaseModel):
    version_code: str
    version_name: str
    bid_price: Optional[Decimal] = None
    bid_quantity: Optional[Decimal] = None
    bid_time_points: list[Any] = []
    trigger_conditions: dict[str, Any] = {}
    fallback_plan: Optional[str] = None
    applicable_scenarios: list[Any] = []
    scenario_strategies: dict[str, Any] = {}
    risk_level: str = "NORMAL"
    pre_authorized_actions: Optional[list[Any]] = None
    risk_notes: Optional[str] = None
    previous_version_id: Optional[UUID] = None


class StrategyUpdate(BaseModel):
    version_code: Optional[str] = None
    version_name: Optional[str] = None
    bid_price: Optional[Decimal] = None
    bid_quantity: Optional[Decimal] = None
    bid_time_points: Optional[list[Any]] = None
    trigger_conditions: Optional[dict[str, Any]] = None
    fallback_plan: Optional[str] = None
    applicable_scenarios: Optional[list[Any]] = None
    scenario_strategies: Optional[dict[str, Any]] = None
    risk_level: Optional[str] = None
    pre_authorized_actions: Optional[list[Any]] = None
    risk_notes: Optional[str] = None
    previous_version_id: Optional[UUID] = None
    # 乐观锁版本号，更新时必须传入
    version: int = 0


class StrategyResponse(BaseModel):
    id: UUID
    auction_id: UUID
    version_code: str
    version_name: str
    status: str
    bid_price: Optional[Decimal]
    bid_quantity: Optional[Decimal]
    bid_time_points: list[Any]
    trigger_conditions: dict[str, Any]
    fallback_plan: Optional[str]
    applicable_scenarios: list[Any]
    scenario_strategies: dict[str, Any]
    risk_level: str
    pre_authorized_actions: Optional[list[Any]]
    risk_notes: Optional[str]
    previous_version_id: Optional[UUID]
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RejectRequest(BaseModel):
    comment: str
