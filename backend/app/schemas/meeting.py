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
