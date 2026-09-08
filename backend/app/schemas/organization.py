from app.schemas.common import BaseSchema
from uuid import UUID

class OrganizationResponse(BaseSchema):
    id: UUID
    name: str
    slug: str
    is_active: bool
