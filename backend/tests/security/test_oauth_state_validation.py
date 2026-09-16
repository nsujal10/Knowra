import pytest
import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.models.base import Base
from app.services.auth_service import AuthService
from app.core.config import settings


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_valid_oauth_state_verification(db_session):
    """
    Asserts that a state parameter generated for Google with a custom redirect
    passes verification and successfully returns the decoded payload.
    """
    auth_svc = AuthService(db_session)

    state = auth_svc.generate_oauth_state(provider="google", redirect_target="/meetings/q3-review")
    assert isinstance(state, str)
    assert len(state) > 20

    payload = auth_svc.verify_oauth_state(state=state, expected_provider="google")
    assert payload["provider"] == "google"
    assert payload["redirect"] == "/meetings/q3-review"
    assert payload["type"] == "oauth_state"
    assert "nonce" in payload


def test_missing_state_rejected(db_session):
    """
    Asserts that an empty or None state parameter is immediately rejected with 400.
    """
    auth_svc = AuthService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.verify_oauth_state(state="", expected_provider="google")
    assert exc_info.value.status_code == 400
    assert "Missing" in exc_info.value.detail


def test_tampered_state_rejected(db_session):
    """
    Asserts that an attacker-modified or forged state token is rejected with 400.
    """
    auth_svc = AuthService(db_session)

    valid_state = auth_svc.generate_oauth_state(provider="google")
    tampered_state = valid_state[:-6] + "xxxxxx"

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.verify_oauth_state(state=tampered_state, expected_provider="google")
    assert exc_info.value.status_code == 400
    assert "Tampered or invalid" in exc_info.value.detail


def test_expired_state_rejected(db_session):
    """
    Asserts that an expired state token is rejected with 400.
    """
    auth_svc = AuthService(db_session)

    # Manually craft an expired state token
    past = datetime.now(timezone.utc) - timedelta(minutes=15)
    expired_payload = {
        "nonce": "old-nonce",
        "provider": "google",
        "redirect": "/",
        "type": "oauth_state",
        "exp": past,
        "iat": past - timedelta(minutes=5),
    }
    expired_state = jwt.encode(
        expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.verify_oauth_state(state=expired_state, expected_provider="google")
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()


def test_provider_mismatch_state_rejected(db_session):
    """
    Asserts that a state generated for Microsoft is rejected if sent to Google callback.
    """
    auth_svc = AuthService(db_session)

    ms_state = auth_svc.generate_oauth_state(provider="microsoft")

    with pytest.raises(HTTPException) as exc_info:
        auth_svc.verify_oauth_state(state=ms_state, expected_provider="google")
    assert exc_info.value.status_code == 400
    assert "provider mismatch" in exc_info.value.detail.lower()
