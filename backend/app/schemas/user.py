from app.schemas.common import BaseSchema
from uuid import UUID

class UserResponse(BaseSchema):
    id: UUID
    email: str
    full_name: str
    is_active: bool
