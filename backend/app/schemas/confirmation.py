from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConfirmationCreate(BaseModel):
    target_type: str
    target_id: UUID
    action: str  # confirm / reject
    comment: Optional[str] = None


class ConfirmationResponse(BaseModel):
    id: UUID
    target_type: str
    target_id: UUID
    action: str
    comment: Optional[str]
    confirmed_by: UUID
    confirmed_at: datetime

    model_config = ConfigDict(from_attributes=True)
