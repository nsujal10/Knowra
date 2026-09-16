import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.models.base import Base
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.models.membership import Membership
from app.models.user_identity import UserIdentity
from app.services.auth_service import AuthService
from app.security.providers.oidc import OIDCUserInfo
from app.security.password import hash_password
from app.core.config import settings


@pytest.fixture
def db_session():
    """In-memory SQLite session with initialized schema and seed roles."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed system roles
    admin_role = Role(
        id=uuid.uuid4(),
        code="ADMIN",
        name="Administrator",
        description="Workspace admin",
    )
    member_role = Role(
        id=uuid.uuid4(),
        code="MEMBER",
        name="Member",
        description="Standard member",
    )
    session.add_all([admin_role, member_role])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_sso_reconcile_links_existing_local_user(db_session):
    """
    Scenario: A user already registered with email and password (e.g. sarah@enterprise.com).
    When they log in via Google SSO with the same email, the system must link the Google
    provider to the existing User row without throwing a duplicate key integrity error.
    """
    auth_svc = AuthService(db_session)

    # 1. Pre-existing local account with organization
    local_user = auth_svc.register(
        email="sarah@enterprise.com",
        password="Password123!",
        full_name="Sarah Connor",
        org_name="Enterprise Corp",
    )
    initial_user_id = local_user.id

    # 2. User logs in via Google OIDC
    google_user_info = OIDCUserInfo(
        sub="google-uid-10029384",
        email="sarah@enterprise.com",
        name="Sarah Connor",
        email_verified=True,
    )

    access_token, refresh_token, user, org_id = auth_svc.reconcile_sso_user(
        provider="google", user_info=google_user_info
    )

    # 3. Assert identity reconciliation
    assert user.id == initial_user_id
    assert user.email == "sarah@enterprise.com"
    assert access_token is not None
    assert refresh_token is not None

    # Verify UserIdentity was created and linked
    linked_identity = (
        db_session.query(UserIdentity)
        .filter(
            UserIdentity.user_id == initial_user_id,
            UserIdentity.provider == "google",
        )
        .first()
    )
    assert linked_identity is not None
    assert linked_identity.provider_user_id == "google-uid-10029384"
    assert linked_identity.provider_email == "sarah@enterprise.com"

    # Verify no duplicate user was created
    total_users = db_session.query(User).filter(User.email == "sarah@enterprise.com").count()
    assert total_users == 1


def test_sso_reconcile_auto_provisions_new_user_and_tenant(db_session):
    """
    Scenario: A completely new user signs in via Microsoft Entra ID.
    The system should derive their organization from the email domain (@acmecorp.com),
    provision a new tenant, create the User, and assign them the ADMIN role.
    """
    auth_svc = AuthService(db_session)

    ms_user_info = OIDCUserInfo(
        sub="ms-entra-oid-998877",
        email="alex.mercer@acmecorp.com",
        name="Alex Mercer",
        email_verified=True,
    )

    access_token, refresh_token, user, org_id = auth_svc.reconcile_sso_user(
        provider="microsoft", user_info=ms_user_info
    )

    assert user.email == "alex.mercer@acmecorp.com"
    assert user.full_name == "Alex Mercer"
    assert user.is_active is True
    assert user.is_verified is True
    assert access_token is not None

    # Verify auto-provisioned organization
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None
    assert "Acmecorp" in org.name

    # Verify ADMIN membership role
    membership = (
        db_session.query(Membership)
        .filter(
            Membership.user_id == user.id,
            Membership.organization_id == org_id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role.code == "ADMIN"

    # Verify identity record
    identity = (
        db_session.query(UserIdentity)
        .filter(UserIdentity.provider == "microsoft", UserIdentity.user_id == user.id)
        .first()
    )
    assert identity is not None
    assert identity.provider_user_id == "ms-entra-oid-998877"


def test_sso_reconcile_subsequent_login_reuses_linked_identity(db_session):
    """
    Scenario: An already-linked SSO user logs in a second time.
    The system must find the UserIdentity and issue tokens without creating duplicates.
    """
    auth_svc = AuthService(db_session)

    user_info = OIDCUserInfo(
        sub="google-uid-relogin",
        email="john@cloudtech.io",
        name="John Doe",
        email_verified=True,
    )

    # First login (provisions user)
    _, _, first_user, org_id = auth_svc.reconcile_sso_user("google", user_info)

    # Second login
    _, _, second_user, second_org_id = auth_svc.reconcile_sso_user("google", user_info)

    assert first_user.id == second_user.id
    assert org_id == second_org_id

    # Verify still exactly 1 user and 1 identity
    assert db_session.query(User).filter(User.email == "john@cloudtech.io").count() == 1
    assert db_session.query(UserIdentity).filter(UserIdentity.provider_user_id == "google-uid-relogin").count() == 1


def test_sso_reconcile_rejects_personal_domains_when_enforced(db_session, monkeypatch):
    """
    Scenario: Strict enterprise domain validation is enabled.
    Users attempting to sign in with personal domains (@gmail.com, @outlook.com)
    must be rejected with HTTP 403 Forbidden.
    """
    auth_svc = AuthService(db_session)

    # Enable strict enterprise domain enforcement
    monkeypatch.setattr(settings, "SSO_ENFORCE_BUSINESS_DOMAINS", True)

    personal_user_info = OIDCUserInfo(
        sub="gmail-uid-1234",
        email="contractor@gmail.com",
        name="Gmail User",
        email_verified=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.reconcile_sso_user("google", personal_user_info)

    assert exc_info.value.status_code == 403
    assert "Personal email domain" in exc_info.value.detail
