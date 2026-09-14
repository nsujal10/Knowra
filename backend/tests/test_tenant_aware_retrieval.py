"""
Integration Tests: Phase 18 Tenant-Aware Knowledge Retrieval
Ensures vector and keyword retrieval never leak knowledge chunks across different tenants.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk
from app.knowledge.retrieval import HybridRetrievalService
from app.models.media_asset import MediaAsset
from app.models.enums import MediaStatus
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


def test_tenant_aware_vector_and_keyword_isolation(db_session):
    # 1. Create two distinct tenants
    uid_a = str(uuid.uuid4())[:6]
    uid_b = str(uuid.uuid4())[:6]
    org_a = Organization(name=f"Tenant Alpha {uid_a}", slug=f"tenant-alpha-{uid_a}")
    org_b = Organization(name=f"Tenant Beta {uid_b}", slug=f"tenant-beta-{uid_b}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    u_a = User(email=f"alpha_{uid_a}@example.com", password_hash="hash", full_name="User Alpha")
    u_b = User(email=f"beta_{uid_b}@example.com", password_hash="hash", full_name="User Beta")
    db_session.add_all([u_a, u_b])
    db_session.flush()

    # 2. Create meetings & media assets for each
    m_a = Meeting(tenant_id=org_a.id, owner_id=u_a.id, title="Alpha Secret Strategy")
    m_b = Meeting(tenant_id=org_b.id, owner_id=u_b.id, title="Beta Public Roadmap")
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
        duration_seconds=120.0,
        provider_name="test",
        model_name="test",
        model_version="1.0",
    )
    t_b = Transcript(
        tenant_id=org_b.id,
        meeting_id=m_b.id,
        media_asset_id=media_b.id,
        language="en",
        duration_seconds=120.0,
        provider_name="test",
        model_name="test",
        model_version="1.0",
    )
    db_session.add_all([t_a, t_b])
    db_session.commit()

    gateway = EmbeddingGateway()
    provider = gateway.get_provider()

    # 3. Add confidential chunk to Tenant A
    content_a = "Confidential Project Titan budget is approved for thirty million dollars."
    chunk_a = KnowledgeChunk(
        tenant_id=org_a.id,
        meeting_id=m_a.id,
        transcript_id=t_a.id,
        content=content_a,
        token_count=12,
        embedding=provider.embed_text(content_a),
    )
    # 4. Add chunk to Tenant B
    content_b = "Quarterly marketing spend on social ads is fifty thousand dollars."
    chunk_b = KnowledgeChunk(
        tenant_id=org_b.id,
        meeting_id=m_b.id,
        transcript_id=t_b.id,
        content=content_b,
        token_count=10,
        embedding=provider.embed_text(content_b),
    )
    db_session.add_all([chunk_a, chunk_b])
    db_session.commit()

    # 5. Execute retrieval as Tenant B querying for 'Project Titan budget'
    service_b = HybridRetrievalService(db=db_session, tenant_id=org_b.id)

    # Vector search check
    vector_results = service_b.search_vector(query="Project Titan budget", limit=5)
    result_ids_v = [c.id for c, _ in vector_results]
    assert chunk_a.id not in result_ids_v, "Cross-tenant leak detected in vector search!"

    # Keyword search check
    keyword_results = service_b.search_keyword(query="Project Titan", limit=5)
    result_ids_k = [c.id for c, _ in keyword_results]
    assert chunk_a.id not in result_ids_k, "Cross-tenant leak detected in keyword search!"

    # Hybrid search check
    hybrid_res = service_b.hybrid_search(query="Project Titan budget", limit=5)
    result_ids_h = [item.chunk_id for item in hybrid_res.results]
    assert chunk_a.id not in result_ids_h, "Cross-tenant leak detected in hybrid search!"

    # 6. Execute retrieval as Tenant A - should find chunk_a
    service_a = HybridRetrievalService(db=db_session, tenant_id=org_a.id)
    hybrid_res_a = service_a.hybrid_search(query="Project Titan budget", limit=5)
    result_ids_a = [item.chunk_id for item in hybrid_res_a.results]
    assert chunk_a.id in result_ids_a, "Tenant A failed to retrieve its own chunk!"
