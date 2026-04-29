from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class RectificationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: UUID
    measures: str  # 必填，不得为空字符串
    due_date: date  # 必填

    @field_validator("measures")
    @classmethod
    def measures_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("measures 不得为空")
        return v

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title 不得为空")
        return v


class RectificationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[UUID] = None
    measures: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    delay_reason: Optional[str] = None
    close_reason: Optional[str] = None
    progress_note: Optional[str] = None  # 进度备注，不持久化到独立字段，可附加到 description


class EvidenceUpload(BaseModel):
    evidence: List[Any]  # 文件路径或说明列表


class ConfirmRequest(BaseModel):
    comment: Optional[str] = None  # 确认备注


class RectificationResponse(BaseModel):
    id: UUID
    retrospective_id: UUID
    title: str
    description: Optional[str]
    assignee_id: UUID
    measures: str
    due_date: date
    status: str
    evidence: List[Any]
    delay_reason: Optional[str]
    close_reason: Optional[str]
    confirmed_by: Optional[UUID]
    confirmed_at: Optional[datetime]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
