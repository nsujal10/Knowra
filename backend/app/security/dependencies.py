from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.security.jwt import decode_access_token
from app.security.exceptions import CredentialsException, ForbiddenException
from app.schemas.auth import CurrentUserContext
from app.repositories.membership_repository import MembershipRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> CurrentUserContext:
    payload = decode_access_token(token)
    user_id = UUID(payload.get("sub"))
    org_id = UUID(payload.get("org"))
    
    membership = MembershipRepository(db).get_by_user_id(user_id)
    if not membership or membership.organization_id != org_id:
        raise CredentialsException(detail="Inactive or mismatched organization")
        
    permissions = [p.code for p in membership.role.permissions]
    
    return CurrentUserContext(
        user_id=user_id,
        organization_id=org_id,
        role_code=membership.role.code,
        permissions=permissions
    )

def require_permission(permission_code: str):
    def permission_checker(current_user: CurrentUserContext = Depends(get_current_user)):
        if permission_code not in current_user.permissions:
            raise ForbiddenException(detail=f"Missing required permission: {permission_code}")
        return current_user
    return permission_checker

def verify_tenant_resource_access(resource_org_id: UUID, current_user: CurrentUserContext = Depends(get_current_user)):
    if resource_org_id != current_user.organization_id:
        raise ForbiddenException(detail="Cross-tenant access denied")
    return True
