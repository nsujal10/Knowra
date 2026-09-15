"""
Test: Cross-Tenant RAG Isolation (Phase 21 & 22)
Asserts that a user in Tenant A cannot retrieve Tenant B's chunks or citations,
even if the user query is an exact semantic match.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.user import User
from app.rag.orchestrator import RAGOrchestrator
from app.rag.schemas import RAGQueryRequest
from app.schemas.auth import CurrentUserContext


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_cross_tenant_rag_isolation(db_session):
    run_id = str(uuid.uuid4())[:8]

    # 1. Provision Tenant Alpha and Tenant Beta
    org_alpha = Organization(name=f"Tenant Alpha {run_id}", slug=f"alpha-{run_id}")
    org_beta = Organization(name=f"Tenant Beta {run_id}", slug=f"beta-{run_id}")
    db_session.add_all([org_alpha, org_beta])
    db_session.commit()

    user_alpha = User(email=f"alpha_{run_id}@example.com", password_hash="hash", full_name="User Alpha")
    user_beta = User(email=f"beta_{run_id}@example.com", password_hash="hash", full_name="User Beta")
    db_session.add_all([user_alpha, user_beta])
    db_session.flush()

    meeting_alpha = Meeting(tenant_id=org_alpha.id, owner_id=user_alpha.id, title="Alpha General Sync")
    meeting_beta = Meeting(tenant_id=org_beta.id, owner_id=user_beta.id, title="Beta Secret Project Phoenix")
    db_session.add_all([meeting_alpha, meeting_beta])
    db_session.flush()

    media_a = MediaAsset(tenant_id=org_alpha.id, meeting_id=meeting_alpha.id, filename="a.wav", original_content_type="audio/wav", status=MediaStatus.READY)
    media_b = MediaAsset(tenant_id=org_beta.id, meeting_id=meeting_beta.id, filename="b.wav", original_content_type="audio/wav", status=MediaStatus.READY)
    db_session.add_all([media_a, media_b])
    db_session.flush()

    t_alpha = Transcript(
        tenant_id=org_alpha.id,
        meeting_id=meeting_alpha.id,
        media_asset_id=media_a.id,
        language="en",
        duration_seconds=120.0,
        provider_name="faster-whisper",
        model_name="small.en",
        model_version="1.0",
    )
    t_beta = Transcript(
        tenant_id=org_beta.id,
        meeting_id=meeting_beta.id,
        media_asset_id=media_b.id,
        language="en",
        duration_seconds=120.0,
        provider_name="faster-whisper",
        model_name="small.en",
        model_version="1.0",
    )
    db_session.add_all([t_alpha, t_beta])
    db_session.flush()

    # 2. Insert highly confidential chunk into Tenant Beta with real embeddings
    gateway = EmbeddingGateway()
    secret_text = "Project Phoenix master encryption key is PHOENIX-SECRET-KEY-994821 and must remain confidential."
    vec_beta = gateway.embed_text(secret_text)

    chunk_beta = KnowledgeChunk(
        tenant_id=org_beta.id,
        meeting_id=meeting_beta.id,
        transcript_id=t_beta.id,
        content=secret_text,
        chunk_index=0,
        token_count=18,
        embedding=vec_beta,
        start_seconds=10.0,
        end_seconds=25.0,
    )
    db_session.add(chunk_beta)
    db_session.commit()

    # 3. Execute RAG query as User Alpha (Tenant Alpha) seeking the confidential secret
    user_alpha_context = CurrentUserContext(
        user_id=user_alpha.id,
        organization_id=org_alpha.id,
        role_code="ADMIN",
        permissions=["meetings:read", "rag:search", "rag:chat"],
    )

    orchestrator = RAGOrchestrator(db=db_session)
    request = RAGQueryRequest(
        query="What is the master encryption key for Project Phoenix?",
        limit=5,
    )

    response_alpha = orchestrator.chat(current_user=user_alpha_context, request=request)

    # 4. Assert 0 leakage to Tenant Alpha
    assert "PHOENIX-SECRET-KEY-994821" not in response_alpha.answer
    assert len(response_alpha.citations) == 0
    assert response_alpha.retrieval_metadata["chunks_retrieved"] == 0

    # 5. Execute identical RAG query as User Beta (Tenant Beta)
    user_beta_context = CurrentUserContext(
        user_id=user_beta.id,
        organization_id=org_beta.id,
        role_code="ADMIN",
        permissions=["meetings:read", "rag:search", "rag:chat"],
    )
    response_beta = orchestrator.chat(current_user=user_beta_context, request=request)

    # 6. Assert Tenant Beta successfully retrieves its own data
    assert response_beta.retrieval_metadata["chunks_retrieved"] >= 1
    assert "PHOENIX-SECRET-KEY-994821" in response_beta.answer or "Project Phoenix" in response_beta.answer
