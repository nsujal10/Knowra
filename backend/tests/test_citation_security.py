"""
Test: Citation IDOR & Meeting-Level RBAC Protection (Phase 21 & 22)
Ensures direct requests to view transcript citations without appropriate
meeting-level RBAC permissions return HTTP 403 Forbidden.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_citation_idor_prevention(db_session):
    client = TestClient(app)
    run_id = str(uuid.uuid4())[:8]

    # 1. Create Organization Alpha and Organization Beta
    org_a = Organization(name=f"Org Alpha {run_id}", slug=f"org-a-{run_id}")
    org_b = Organization(name=f"Org Beta {run_id}", slug=f"org-b-{run_id}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    user_a = User(email=f"user_a_{run_id}@example.com", password_hash="hash", full_name="User A")
    user_restricted = User(email=f"user_restr_{run_id}@example.com", password_hash="hash", full_name="Restricted User")
    user_b = User(email=f"user_b_{run_id}@example.com", password_hash="hash", full_name="User B")
    db_session.add_all([user_a, user_restricted, user_b])
    db_session.flush()

    # Meeting 1 in Org A (owned by user_a)
    m_a1 = Meeting(tenant_id=org_a.id, owner_id=user_a.id, title="Alpha Private Executive Strategy")
    # Meeting 2 in Org B
    m_b1 = Meeting(tenant_id=org_b.id, owner_id=user_b.id, title="Beta Confidential Meeting")
    db_session.add_all([m_a1, m_b1])
    db_session.flush()

    media_a = MediaAsset(tenant_id=org_a.id, meeting_id=m_a1.id, filename="a.wav", original_content_type="audio/wav", status=MediaStatus.READY)
    media_b = MediaAsset(tenant_id=org_b.id, meeting_id=m_b1.id, filename="b.wav", original_content_type="audio/wav", status=MediaStatus.READY)
    db_session.add_all([media_a, media_b])
    db_session.flush()

    t_a = Transcript(
        tenant_id=org_a.id,
        meeting_id=m_a1.id,
        media_asset_id=media_a.id,
        language="en",
        duration_seconds=120.0,
        provider_name="faster-whisper",
        model_name="small.en",
        model_version="1.0",
    )
    t_b = Transcript(
        tenant_id=org_b.id,
        meeting_id=m_b1.id,
        media_asset_id=media_b.id,
        language="en",
        duration_seconds=120.0,
        provider_name="faster-whisper",
        model_name="small.en",
        model_version="1.0",
    )
    db_session.add_all([t_a, t_b])
    db_session.flush()

    # Segments
    seg_a = TranscriptSegment(
        tenant_id=org_a.id,
        transcript_id=t_a.id,
        sequence_number=0,
        start_seconds=1.0,
        end_seconds=4.0,
        confidence=0.95,
        text="Alpha secret acquisition discussion segment",
    )
    seg_b = TranscriptSegment(
        tenant_id=org_b.id,
        transcript_id=t_b.id,
        sequence_number=0,
        start_seconds=10.0,
        end_seconds=15.0,
        confidence=0.95,
        text="Beta proprietary architecture segment",
    )
    db_session.add_all([seg_a, seg_b])
    db_session.commit()

    # Case 1: Cross-Tenant IDOR Attack
    # User in Org A tries to access Citation Segment belonging to Org B
    ctx_user_a = CurrentUserContext(
        user_id=user_a.id,
        organization_id=org_a.id,
        role_code="ADMIN",
        permissions=["meetings:read", "rag:search"],
    )
    app.dependency_overrides[get_current_user] = lambda: ctx_user_a

    resp = client.get(f"/api/v1/chat/citations/{seg_b.id}")
    assert resp.status_code == 403
    assert "access to transcript citation denied" in resp.json()["detail"].lower()

    # Case 2: Intra-Tenant Restricted RBAC IDOR
    # Restricted Employee in Org A tries to view meeting citation owned by User A
    ctx_restricted = CurrentUserContext(
        user_id=user_restricted.id,
        organization_id=org_a.id,
        role_code="EMPLOYEE",
        permissions=["meetings:read", "rag:search"],
    )
    app.dependency_overrides[get_current_user] = lambda: ctx_restricted

    resp_restricted = client.get(f"/api/v1/chat/citations/{seg_a.id}")
    assert resp_restricted.status_code == 403
    assert "access to transcript citation denied" in resp_restricted.json()["detail"].lower()

    # Case 3: Legitimate Authorized Access
    # Owner of Meeting A requests citation
    app.dependency_overrides[get_current_user] = lambda: ctx_user_a
    resp_authorized = client.get(f"/api/v1/chat/citations/{seg_a.id}")
    assert resp_authorized.status_code == 200
    data = resp_authorized.json()
    assert data["segment_id"] == str(seg_a.id)
    assert data["text"] == "Alpha secret acquisition discussion segment"

    app.dependency_overrides.clear()
