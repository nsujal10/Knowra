"""
Integration Test: Tenant Vector Isolation (Phase 19 / Phase 20)
Proves that queries from Tenant A cannot retrieve pgvector chunks owned by Tenant B
under any semantic similarity score.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.embeddings.models import KnowledgeEmbedding
from app.knowledge.models import KnowledgeChunk
from app.knowledge.retrieval.vector import VectorSearchEngine
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.user import User


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_tenant_vector_isolation_under_identical_similarity(db_session):
    # 1. Setup Tenant A and Tenant B
    run_id = str(uuid.uuid4())[:8]
    org_a = Organization(name=f"Tenant Vector Alpha {run_id}", slug=f"tenant-vec-a-{run_id}")
    org_b = Organization(name=f"Tenant Vector Beta {run_id}", slug=f"tenant-vec-b-{run_id}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    user_a = User(email=f"alpha_vec_{run_id}@example.com", password_hash="hash", full_name="User Alpha")
    user_b = User(email=f"beta_vec_{run_id}@example.com", password_hash="hash", full_name="User Beta")
    db_session.add_all([user_a, user_b])
    db_session.flush()

    m_a = Meeting(tenant_id=org_a.id, owner_id=user_a.id, title="Alpha Secret Strategy")
    m_b = Meeting(tenant_id=org_b.id, owner_id=user_b.id, title="Beta Highly Classified Roadmap")
    db_session.add_all([m_a, m_b])
    db_session.flush()

    media_a = MediaAsset(tenant_id=org_a.id, meeting_id=m_a.id, filename="a.wav", original_content_type="audio/wav", status=MediaStatus.READY)
    media_b = MediaAsset(tenant_id=org_b.id, meeting_id=m_b.id, filename="b.wav", original_content_type="audio/wav", status=MediaStatus.READY)
    db_session.add_all([media_a, media_b])
    db_session.flush()

    t_a = Transcript(
        tenant_id=org_a.id,
        meeting_id=m_a.id,
        media_asset_id=media_a.id,
        language="en",
        duration_seconds=60.0,
        provider_name="faster-whisper",
        model_name="base",
        model_version="1.0",
    )
    t_b = Transcript(
        tenant_id=org_b.id,
        meeting_id=m_b.id,
        media_asset_id=media_b.id,
        language="en",
        duration_seconds=60.0,
        provider_name="faster-whisper",
        model_name="base",
        model_version="1.0",
    )
    db_session.add_all([t_a, t_b])
    db_session.flush()

    # Highly specific text planted in Tenant B's chunk
    secret_text = "Project Prometheus: Autonomous orbital quantum core architecture with nuclear fail-safes."
    alpha_text = "General discussion regarding office lunch catering and weekly sprint goals."

    gateway = EmbeddingGateway()
    vec_b = gateway.embed_text(secret_text)
    vec_a = gateway.embed_text(alpha_text)

    chunk_b = KnowledgeChunk(
        tenant_id=org_b.id,
        meeting_id=m_b.id,
        transcript_id=t_b.id,
        content=secret_text,
        chunk_index=0,
        token_count=len(secret_text.split()),
        primary_topic="Quantum Core",
        start_seconds=0.0,
        end_seconds=10.0,
        embedding=vec_b,
    )
    chunk_a = KnowledgeChunk(
        tenant_id=org_a.id,
        meeting_id=m_a.id,
        transcript_id=t_a.id,
        content=alpha_text,
        chunk_index=0,
        token_count=len(alpha_text.split()),
        primary_topic="Office Logistics",
        start_seconds=0.0,
        end_seconds=5.0,
        embedding=vec_a,
    )
    db_session.add_all([chunk_a, chunk_b])
    db_session.flush()

    emb_b = KnowledgeEmbedding(
        tenant_id=org_b.id,
        chunk_id=chunk_b.id,
        meeting_id=m_b.id,
        provider_name=gateway.provider_name,
        model_name=gateway.model_name,
        model_version=gateway.model_version,
        dimensions=gateway.dimension,
        embedding=vec_b,
        content_hash=gateway.compute_content_hash(secret_text),
    )
    emb_a = KnowledgeEmbedding(
        tenant_id=org_a.id,
        chunk_id=chunk_a.id,
        meeting_id=m_a.id,
        provider_name=gateway.provider_name,
        model_name=gateway.model_name,
        model_version=gateway.model_version,
        dimensions=gateway.dimension,
        embedding=vec_a,
        content_hash=gateway.compute_content_hash(alpha_text),
    )
    db_session.add_all([emb_a, emb_b])
    db_session.commit()

    # 2. Query as Tenant A using the exact text from Tenant B's secret
    # This query vector has ~1.0 cosine similarity to Tenant B's chunk
    engine_a = VectorSearchEngine(db=db_session, tenant_id=org_a.id)
    results_a = engine_a.search(query=secret_text, limit=10)

    # 3. Assert Tenant B's chunk NEVER leaks into Tenant A's result set
    returned_chunk_ids = [res_chunk.id for res_chunk, _score in results_a]
    assert chunk_b.id not in returned_chunk_ids, "CRITICAL: Cross-tenant vector leakage detected!"

    for res_chunk, _score in results_a:
        assert res_chunk.tenant_id == org_a.id, f"Invalid tenant leak: {res_chunk.tenant_id} != {org_a.id}"

    # 4. Query as Tenant B using the same query text - Tenant B must find its own chunk
    engine_b = VectorSearchEngine(db=db_session, tenant_id=org_b.id)
    results_b = engine_b.search(query=secret_text, limit=10)

    returned_b_ids = [res_chunk.id for res_chunk, _score in results_b]
    assert chunk_b.id in returned_b_ids, "Tenant B failed to retrieve its own relevant chunk!"
    assert results_b[0][0].id == chunk_b.id
