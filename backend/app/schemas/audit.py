from app.schemas.common import BaseSchema
from uuid import UUID
from datetime import datetime

class AuditLogResponse(BaseSchema):
    id: UUID
    action: str
    created_at: datetime
