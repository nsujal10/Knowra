from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.schemas.common import BaseSchema

class MeetingCreate(BaseModel):
    title: str

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class MeetingResponse(BaseSchema):
    id: UUID
    title: str
    status: str
    owner_id: UUID
    created_at: datetime

class MeetingListResponse(BaseModel):
    items: list[MeetingResponse]
    total: int
    page: int = 1
    page_size: int = 10
    has_more: bool = False
