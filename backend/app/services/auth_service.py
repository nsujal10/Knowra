import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from app.core.config import settings
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.refresh_session import RefreshSession
from app.security.password import hash_password, verify_password
from app.security.jwt import create_access_token
from app.security.exceptions import CredentialsException
from app.services.audit_service import AuditService
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.refresh_session_repository import RefreshSessionRepository

def generate_refresh_token() -> tuple[str, str]:
    plain_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    return plain_token, token_hash

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.session_repo = RefreshSessionRepository(db)

    def register(self, email: str, password: str, full_name: str, org_name: str):
        try:
            # Create User
            user = User(email=email, password_hash=hash_password(password), full_name=full_name)
            self.db.add(user)
            
            # Create Org
            slug = org_name.lower().replace(" ", "-") + "-" + secrets.token_hex(4)
            org = Organization(name=org_name, slug=slug)
            self.db.add(org)
            self.db.flush()
            
            # Get Admin Role
            admin_role = self.role_repo.get_by_code("ADMIN")
            if not admin_role:
                raise Exception("System roles not seeded")
                
            # Create Membership
            membership = Membership(user_id=user.id, organization_id=org.id, role_id=admin_role.id)
            self.db.add(membership)
            
            self.db.commit()
            self.audit.log("USER_REGISTERED", user_id=user.id, org_id=org.id)
            return user
        except IntegrityError:
            self.db.rollback()
            raise CredentialsException(detail="Email or Organization already exists")

    def login(self, email: str, password: str):
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            self.audit.log("LOGIN_FAILED", metadata_json={"email": email}, success=False)
            raise CredentialsException()

        membership = self.membership_repo.get_by_user_id(user.id)
        if not membership:
            raise CredentialsException(detail="No active organization found")

        plain_refresh, hash_refresh = generate_refresh_token()
        session = RefreshSession(
            user_id=user.id,
            organization_id=membership.organization_id,
            token_hash=hash_refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(session)
        
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        
        access_token, _ = create_access_token(user.id, session.id, membership.organization_id)
        self.audit.log("LOGIN_SUCCESS", user_id=user.id, org_id=membership.organization_id)
        
        return access_token, plain_refresh

    def refresh_token(self, plain_refresh: str):
        token_hash = hashlib.sha256(plain_refresh.encode()).hexdigest()
        session = self.session_repo.get_by_hash(token_hash)
        
        if not session:
            raise CredentialsException()
            
        if session.revoked_at:
            # BREACH DETECTED: Revoke token family
            self.db.query(RefreshSession).filter(RefreshSession.user_id == session.user_id).update(
                {"revoked_at": datetime.now(timezone.utc)}
            )
            self.db.commit()
            self.audit.log("TOKEN_REUSE_DETECTED", user_id=session.user_id, success=False)
            raise CredentialsException(detail="Session compromised")
            
        if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise CredentialsException(detail="Refresh token expired")

        # Rotate
        session.revoked_at = datetime.now(timezone.utc)
        
        new_plain, new_hash = generate_refresh_token()
        new_session = RefreshSession(
            user_id=session.user_id,
            organization_id=session.organization_id,
            token_hash=new_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(new_session)
        self.db.flush()
        
        session.replaced_by = new_session.id
        self.db.commit()
        
        access_token, _ = create_access_token(session.user_id, new_session.id, session.organization_id)
        return access_token, new_plain
        
    def logout(self, user_id: uuid.UUID, all_sessions: bool = False):
        if all_sessions:
            self.db.query(RefreshSession).filter(RefreshSession.user_id == user_id, RefreshSession.revoked_at == None).update(
                {"revoked_at": datetime.now(timezone.utc)}
            )
        self.db.commit()
