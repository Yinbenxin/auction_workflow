from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModificationCreate(BaseModel):
    strategy_version_id: UUID
    affected_fields: list = []
    before_value: dict = {}
    after_value: dict = {}
    reason: str  # 必填
    impact_scope: str  # 必填
    risk_notes: Optional[str] = None
    attachments: list = []


class EmergencyExecuteRequest(BaseModel):
    strategy_version_id: UUID
    reason: str
    impact_scope: str
    affected_fields: list = []
    before_value: dict = {}
    after_value: dict = {}
    is_pre_authorized: bool = False
    matched_emergency_rule_id: Optional[str] = None


class ApproveRequest(BaseModel):
    approval_comment: Optional[str] = None


class RejectRequest(BaseModel):
    comment: str  # 必填


class ReviewRequest(BaseModel):
    review_comment: Optional[str] = None


class ExecuteRequest(BaseModel):
    execution_result: Optional[str] = None


class PostExplanationRequest(BaseModel):
    post_explanation: Optional[str] = None
    deviation_reason: Optional[str] = None


class ModificationResponse(BaseModel):
    id: UUID
    auction_id: UUID
    strategy_version_id: UUID
    status: str
    affected_fields: list
    before_value: dict
    after_value: dict
    reason: str
    impact_scope: str
    risk_notes: Optional[str]
    is_emergency: bool
    is_pre_authorized: Optional[bool]
    matched_emergency_rule_id: Optional[str]
    deviation_reason: Optional[str]
    post_explanation: Optional[str]
    attachments: list
    requested_by: UUID
    requested_at: datetime
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    approval_comment: Optional[str]
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    review_comment: Optional[str]
    executed_by: Optional[UUID]
    executed_at: Optional[datetime]
    execution_result: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
