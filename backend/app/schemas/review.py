from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReviewCreate(BaseModel):
    """发起执行前复核（trader 角色）。"""

    strategy_version_id: Optional[UUID] = None


class ChecklistUpdate(BaseModel):
    """更新复核清单勾选状态（reviewer 角色）。"""

    checklist: Dict[str, Any]


class ReviewSubmit(BaseModel):
    """提交复核结论（reviewer 角色）。"""

    status: Literal["passed", "failed"]
    comment: Optional[str] = None


class PreExecutionReviewResponse(BaseModel):
    id: UUID
    auction_id: UUID
    strategy_version_id: Optional[UUID]
    checklist: Dict[str, Any]
    status: str
    configurer_id: UUID
    reviewer_id: Optional[UUID]
    reviewed_at: Optional[datetime]
    comment: Optional[str]

    model_config = ConfigDict(from_attributes=True)
