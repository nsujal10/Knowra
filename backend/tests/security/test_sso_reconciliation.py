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
from app.security.exceptions import CredentialsException
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
    Scenario: A user already registered with email and password (sarah@softude.com).
    When they log in via Google SSO with the same email, the system must link the Google
    provider to the existing User row without throwing a duplicate key integrity error.
    """
    auth_svc = AuthService(db_session)

    # 1. Pre-existing local account with organization
    local_user = auth_svc.register(
        email="sarah@softude.com",
        password="Password123!",
        full_name="Sarah Connor",
        org_name="Softude Tech",
    )
    initial_user_id = local_user.id

    # 2. User logs in via Google OIDC
    google_user_info = OIDCUserInfo(
        sub="google-uid-10029384",
        email="sarah@softude.com",
        name="Sarah Connor",
        email_verified=True,
    )

    access_token, refresh_token, user, org_id = auth_svc.reconcile_sso_user(
        provider="google", user_info=google_user_info
    )

    # 3. Assert identity reconciliation
    assert user.id == initial_user_id
    assert user.email == "sarah@softude.com"
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
    assert linked_identity.provider_email == "sarah@softude.com"

    # Verify no duplicate user was created
    total_users = db_session.query(User).filter(User.email == "sarah@softude.com").count()
    assert total_users == 1


def test_sso_reconcile_auto_provisions_new_user_and_tenant(db_session):
    """
    Scenario: A completely new user signs in via Microsoft Entra ID with softude.com.
    The system should derive their organization from the email domain (@softude.com),
    provision a new tenant, create the User, and assign them the ADMIN role.
    """
    auth_svc = AuthService(db_session)

    ms_user_info = OIDCUserInfo(
        sub="ms-entra-oid-998877",
        email="alex.mercer@softude.com",
        name="Alex Mercer",
        email_verified=True,
    )

    access_token, refresh_token, user, org_id = auth_svc.reconcile_sso_user(
        provider="microsoft", user_info=ms_user_info
    )

    assert user.email == "alex.mercer@softude.com"
    assert user.full_name == "Alex Mercer"
    assert user.is_active is True
    assert user.is_verified is True
    assert access_token is not None

    # Verify auto-provisioned organization
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None
    assert "Softude" in org.name

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
        email="john@softude.com",
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
    assert db_session.query(User).filter(User.email == "john@softude.com").count() == 1
    assert db_session.query(UserIdentity).filter(UserIdentity.provider_user_id == "google-uid-relogin").count() == 1


def test_sso_reconcile_rejects_non_softude_domain(db_session):
    """
    Scenario: Any SSO login attempt with an email domain other than softude.com
    must be strictly rejected with HTTP 403 Forbidden.
    """
    auth_svc = AuthService(db_session)

    external_user_info = OIDCUserInfo(
        sub="google-uid-external",
        email="user@externalcompany.com",
        name="External User",
        email_verified=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.reconcile_sso_user("google", external_user_info)

    assert exc_info.value.status_code == 403
    assert "Access restricted to @softude.com" in exc_info.value.detail


def test_local_register_rejects_non_softude_domain(db_session):
    """
    Scenario: Standard local registration with a non-softude.com email
    must be rejected with HTTP 400 Bad Request.
    """
    auth_svc = AuthService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.register(
            email="hacker@gmail.com",
            password="Password123!",
            full_name="Hacker Man",
            org_name="Hacker Org",
        )

    assert exc_info.value.status_code == 400
    assert "Registration is restricted to @softude.com" in exc_info.value.detail


def test_local_login_rejects_non_softude_domain(db_session):
    """
    Scenario: Standard local login with a non-softude.com email
    must be rejected with CredentialsException.
    """
    auth_svc = AuthService(db_session)

    with pytest.raises(CredentialsException) as exc_info:
        auth_svc.login("user@yahoo.com", "Password123!")

    assert "Access is restricted to @softude.com" in exc_info.value.detail
