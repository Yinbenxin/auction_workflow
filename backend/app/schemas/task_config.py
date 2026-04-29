from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskConfigUpdate(BaseModel):
    strategy_version_id: UUID
    tasks: list = []
    attachments: list = []


class TaskConfigResponse(BaseModel):
    id: UUID
    auction_id: UUID
    strategy_version_id: UUID
    tasks: list
    attachments: list
    status: str
    configured_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
