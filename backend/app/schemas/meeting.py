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
    media_filename: Optional[str] = None
    media_status: Optional[str] = None
    source: Optional[str] = "UPLOAD"

class MeetingListResponse(BaseModel):
    items: list[MeetingResponse]
    total: int
    page: int = 1
    page_size: int = 10
    has_more: bool = False
