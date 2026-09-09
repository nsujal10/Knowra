from pydantic import BaseModel
from uuid import UUID
from fastapi import Depends
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

class TenantContext(BaseModel):
    tenant_id: UUID
    user_id: UUID

def get_tenant_context(current_user: CurrentUserContext = Depends(get_current_user)) -> TenantContext:
    """
    Derives the tenant context exclusively from the server-verified JWT token.
    Never trusts client headers or URL parameters.
    """
    return TenantContext(
        tenant_id=current_user.organization_id,
        user_id=current_user.user_id
    )
