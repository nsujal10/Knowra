from pydantic import BaseModel
from typing import List, Dict
from uuid import UUID
from datetime import datetime
from app.schemas.common import BaseSchema

class MediaUploadRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    parts_count: int

class PartUrl(BaseModel):
    part_number: int
    upload_url: str

class MediaUploadResponse(BaseSchema):
    media_id: UUID
    upload_id: str
    parts: List[PartUrl]

class PartETag(BaseModel):
    part_number: int
    etag: str

class MediaCompleteRequest(BaseModel):
    upload_id: str
    parts: List[PartETag]

class MediaStatusResponse(BaseSchema):
    id: UUID
    status: str
    filename: str
    created_at: datetime
