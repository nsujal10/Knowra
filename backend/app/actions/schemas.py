from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ActionItemEvidenceSchema(BaseModel):
    id: UUID
    segment_id: UUID
    snippet: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionItemEventSchema(BaseModel):
    id: UUID
    actor_user_id: Optional[UUID] = None
    event_type: str
    previous_state: Optional[dict] = None
    new_state: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionItemCommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1)


class ActionItemCommentSchema(BaseModel):
    id: UUID
    user_id: UUID
    comment_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionItemCreate(BaseModel):
    meeting_id: UUID
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    due_date: Optional[datetime] = None
    due_date_raw: Optional[str] = None
    owner_id: Optional[UUID] = None
    owner_raw: Optional[str] = None
    evidence_segment_ids: List[UUID] = Field(default_factory=list)


class ActionItemConfirmRequest(BaseModel):
    owner_id: Optional[UUID] = Field(None, description="Explicitly confirmed user UUID. If null, uses candidate match.")
    due_date: Optional[datetime] = Field(None, description="Confirmed or overridden due date")
    title: Optional[str] = Field(None, description="Confirmed or edited title")
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|URGENT)$")


class ActionItemStatusTransitionRequest(BaseModel):
    status: str = Field(..., pattern="^(REVIEW_REQUIRED|OPEN|IN_PROGRESS|COMPLETED|CANCELLED)$")
    reason: Optional[str] = None


class ActionItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    due_date: Optional[datetime] = None
    owner_id: Optional[UUID] = None


class ActionItemResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    meeting_id: UUID
    intelligence_run_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    due_date_raw: Optional[str] = None
    owner_raw: Optional[str] = None
    owner_id: Optional[UUID] = None
    owner_candidate_user_id: Optional[UUID] = None
    owner_candidate_speaker_id: Optional[UUID] = None
    owner_confidence: Optional[float] = None
    fingerprint_hash: str
    is_confirmed: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    evidence_items: List[ActionItemEvidenceSchema] = Field(default_factory=list)
    events: List[ActionItemEventSchema] = Field(default_factory=list)
    comments: List[ActionItemCommentSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ActionItemListResponse(BaseModel):
    items: List[ActionItemResponse]
    total: int
