import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid
import jwt
from fastapi import HTTPException, status

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
from app.repositories.user_identity_repository import UserIdentityRepository
from app.security.providers.oidc import OIDCUserInfo

BLOCKED_PERSONAL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "ymail.com",
    "aol.com",
    "icloud.com",
    "mail.com",
    "protonmail.com",
    "zoho.com",
}


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
        self.identity_repo = UserIdentityRepository(db)

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

    def generate_oauth_state(self, provider: str, redirect_target: str = "/") -> str:
        """Generates a tamper-proof signed JWT containing state nonce, provider, and redirect target."""
        now = datetime.now(timezone.utc)
        payload = {
            "nonce": secrets.token_hex(16),
            "provider": provider.lower(),
            "redirect": redirect_target or "/",
            "type": "oauth_state",
            "exp": now + timedelta(minutes=10),
            "iat": now,
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def verify_oauth_state(self, state: str, expected_provider: str) -> dict:
        """Verifies the OAuth CSRF state parameter token signature and expiration."""
        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required OAuth state parameter",
            )
        try:
            payload = jwt.decode(
                state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != "oauth_state":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid state token type",
                )
            if payload.get("provider") != expected_provider.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"OAuth provider mismatch in state parameter. Expected {expected_provider}",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state parameter has expired. Please initiate sign-in again.",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tampered or invalid OAuth state parameter",
            )

    def reconcile_sso_user(
        self, provider: str, user_info: OIDCUserInfo
    ) -> tuple[str, str, User, uuid.UUID]:
        """
        Executes enterprise identity reconciliation:
        1. Validates business email domain if enterprise strictness is enabled.
        2. Links to existing User if matching email exists (prevents duplicate key errors).
        3. Auto-provisions Tenant & User with ADMIN role if account does not exist.
        4. Issues Knowra short-lived access JWT and opaque refresh session.
        """
        normalized_provider = provider.lower().strip()
        email = user_info.email.lower().strip()
        domain = email.split("@")[-1] if "@" in email else ""

        # 1. Enterprise domain validation
        if settings.SSO_ENFORCE_BUSINESS_DOMAINS and domain in BLOCKED_PERSONAL_DOMAINS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Personal email domain '@{domain}' is not permitted. Please use your corporate or enterprise work email.",
            )

        # 2. Check if this provider identity already exists
        identity = self.identity_repo.get_by_provider_and_id(
            normalized_provider, user_info.sub
        )

        user: User | None = None
        if identity:
            user = self.user_repo.get_by_id(identity.user_id)
            if user:
                user.last_login_at = datetime.now(timezone.utc)
                user.is_verified = True
                identity.metadata_json = user_info.raw_claims
                self.db.commit()
                self.audit.log(
                    "SSO_LOGIN_SUCCESS",
                    user_id=user.id,
                    metadata_json={"provider": normalized_provider},
                )

        if not user:
            # 3. Check for existing local account with identical email (Account Linking)
            user = self.user_repo.get_by_email(email)
            if user:
                # Securely link the identity to the existing user record
                self.identity_repo.create(
                    user_id=user.id,
                    provider=normalized_provider,
                    provider_user_id=user_info.sub,
                    provider_email=email,
                    metadata_json=user_info.raw_claims,
                )
                user.is_verified = True
                user.last_login_at = datetime.now(timezone.utc)
                self.db.commit()
                self.audit.log(
                    "SSO_ACCOUNT_LINKED",
                    user_id=user.id,
                    metadata_json={"provider": normalized_provider},
                )
            else:
                # 4. Auto-provision Tenant & User
                org_display_name = (
                    domain.split(".")[0].capitalize() + " Workspace"
                    if domain and domain not in BLOCKED_PERSONAL_DOMAINS
                    else f"{(user_info.name or 'Team')}'s Workspace"
                )

                user = User(
                    email=email,
                    password_hash="!sso_managed_account",
                    full_name=user_info.name or email.split("@")[0],
                    is_active=True,
                    is_verified=True,
                    last_login_at=datetime.now(timezone.utc),
                )
                self.db.add(user)
                self.db.flush()

                slug = (
                    org_display_name.lower().replace(" ", "-")
                    + "-"
                    + secrets.token_hex(4)
                )
                org = Organization(name=org_display_name, slug=slug)
                self.db.add(org)
                self.db.flush()

                admin_role = self.role_repo.get_by_code("ADMIN")
                if not admin_role:
                    raise CredentialsException(detail="System roles not seeded")

                membership = Membership(
                    user_id=user.id,
                    organization_id=org.id,
                    role_id=admin_role.id,
                )
                self.db.add(membership)
                self.db.flush()

                self.identity_repo.create(
                    user_id=user.id,
                    provider=normalized_provider,
                    provider_user_id=user_info.sub,
                    provider_email=email,
                    metadata_json=user_info.raw_claims,
                )
                self.db.commit()
                self.audit.log(
                    "SSO_USER_PROVISIONED",
                    user_id=user.id,
                    org_id=org.id,
                    metadata_json={"provider": normalized_provider},
                )

        # 5. Retrieve user's organization membership
        membership = self.membership_repo.get_by_user_id(user.id)
        if not membership:
            raise CredentialsException(detail="No active organization found for user")

        # 6. Issue Knowra session tokens
        plain_refresh, hash_refresh = generate_refresh_token()
        session = RefreshSession(
            user_id=user.id,
            organization_id=membership.organization_id,
            token_hash=hash_refresh,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(session)
        self.db.commit()

        access_token, _ = create_access_token(
            user.id, session.id, membership.organization_id
        )

        return access_token, plain_refresh, user, membership.organization_id

