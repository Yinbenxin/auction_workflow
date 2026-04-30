from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskConfigUpdate(BaseModel):
    strategy_version_id: Optional[UUID] = None
    tasks: list = []
    attachments: list = []


class TaskConfigApprovalRequest(BaseModel):
    comment: Optional[str] = None


class TaskConfigResponse(BaseModel):
    id: UUID
    auction_id: UUID
    strategy_version_id: Optional[UUID] = None
    tasks: list
    attachments: list
    status: str
    configured_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
