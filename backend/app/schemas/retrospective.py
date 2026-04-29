from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RetrospectiveCreate(BaseModel):
    strategy_version_id: UUID
    basic_info: dict = {}
    strategy_summary: dict = {}
    execution_summary: dict = {}
    transaction_result: dict = {}
    deviation_analysis: Optional[str] = None
    anomaly_records: Optional[str] = None
    confirmation_records: Optional[str] = None
    root_cause: Optional[str] = None
    improvement_actions: Optional[str] = None
    strategy_learnings: Optional[str] = None
    emergency_explanation: Optional[str] = None


class RetrospectiveUpdate(BaseModel):
    strategy_version_id: Optional[UUID] = None
    basic_info: Optional[dict] = None
    strategy_summary: Optional[dict] = None
    execution_summary: Optional[dict] = None
    transaction_result: Optional[dict] = None
    deviation_analysis: Optional[str] = None
    anomaly_records: Optional[str] = None
    confirmation_records: Optional[str] = None
    root_cause: Optional[str] = None
    improvement_actions: Optional[str] = None
    strategy_learnings: Optional[str] = None
    emergency_explanation: Optional[str] = None


class RetrospectiveResponse(BaseModel):
    id: UUID
    auction_id: UUID
    strategy_version_id: UUID
    basic_info: dict
    strategy_summary: dict
    execution_summary: dict
    transaction_result: dict
    deviation_analysis: Optional[str]
    anomaly_records: Optional[str]
    confirmation_records: Optional[str]
    root_cause: Optional[str]
    improvement_actions: Optional[str]
    strategy_learnings: Optional[str]
    emergency_explanation: Optional[str]
    status: str
    created_by: UUID
    submitted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
