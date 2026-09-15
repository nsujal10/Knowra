"""
Unit / Integration Test: Graph-Aware RAG Fusion (Phase 24)
Verifies that the RAG pipeline correctly fuses graph relationships
with dense semantic retrieval for complex organizational queries.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.retrieval.traversal import GraphTraversalEngine
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk
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


def test_graph_aware_rag_fusion(db_session):
    run_id = str(uuid.uuid4())[:8]

    # 1. Setup Tenant and User
    org = Organization(name=f"Graph Fusion Org {run_id}", slug=f"graph-fusion-{run_id}")
    db_session.add(org)
    db_session.commit()

    user = User(email=f"arch_{run_id}@fusion.com", password_hash="hash", full_name="Chief Architect")
    db_session.add(user)
    db_session.flush()

    meeting = Meeting(tenant_id=org.id, owner_id=user.id, title="Project Apollo Architecture Review")
    db_session.add(meeting)
    db_session.flush()

    media = MediaAsset(tenant_id=org.id, meeting_id=meeting.id, filename="rev.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
    db_session.add(media)
    db_session.flush()

    transcript = Transcript(tenant_id=org.id, meeting_id=meeting.id, media_asset_id=media.id, language="en", duration_seconds=120.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
    db_session.add(transcript)
    db_session.flush()

    seg = TranscriptSegment(
        tenant_id=org.id, transcript_id=transcript.id, sequence_number=0, start_seconds=10.0, end_seconds=25.0,
        text="David Miller confirmed that Project Apollo will adopt pgvector for search infrastructure.", confidence=0.98
    )
    db_session.add(seg)
    db_session.flush()

    # 2. Knowledge Chunk with Vector
    gateway = EmbeddingGateway()
    vec = gateway.embed_text(seg.text)
    chunk = KnowledgeChunk(
        tenant_id=org.id, meeting_id=meeting.id, transcript_id=transcript.id,
        content=seg.text, chunk_index=0, token_count=14, embedding=vec, start_seconds=10.0, end_seconds=25.0
    )
    db_session.add(chunk)
    db_session.flush()

    # 3. Setup Knowledge Graph Nodes and Edges
    person_node = KnowledgeEntity(tenant_id=org.id, name="David Miller", canonical_name="David Miller", entity_type="PERSON")
    project_node = KnowledgeEntity(tenant_id=org.id, name="Project Apollo", canonical_name="Project Apollo", entity_type="PROJECT")
    tech_node = KnowledgeEntity(tenant_id=org.id, name="pgvector", canonical_name="Pgvector", entity_type="TECHNOLOGY")
    db_session.add_all([person_node, project_node, tech_node])
    db_session.flush()

    edge1 = KnowledgeRelationship(
        tenant_id=org.id, source_entity_id=person_node.id, target_entity_id=project_node.id,
        relationship_type="LEADS", meeting_id=meeting.id, evidence_segment_id=seg.id
    )
    edge2 = KnowledgeRelationship(
        tenant_id=org.id, source_entity_id=project_node.id, target_entity_id=tech_node.id,
        relationship_type="USES_TECHNOLOGY", meeting_id=meeting.id, evidence_segment_id=seg.id
    )
    db_session.add_all([edge1, edge2])
    db_session.commit()

    # 4. Verify GraphTraversalEngine extracts relationship facts
    engine = GraphTraversalEngine(db=db_session, tenant_id=org.id)
    facts = engine.get_graph_context_for_query("What technology does Project Apollo use?")
    assert len(facts) >= 1
    assert any("USES_TECHNOLOGY" in f for f in facts)
    assert any("Pgvector" in f or "pgvector" in f for f in facts)

    # 5. Execute RAG Chat with Graph Fusion
    ctx = CurrentUserContext(
        user_id=user.id,
        organization_id=org.id,
        role_code="ADMIN",
        permissions=["meetings:read", "rag:search", "rag:chat"],
    )
    orchestrator = RAGOrchestrator(db=db_session)
    request = RAGQueryRequest(
        query="What decisions and technology choices were made for Project Apollo?",
        limit=5,
    )

    response = orchestrator.chat(current_user=ctx, request=request)

    assert response.retrieval_metadata.get("graph_relationships_fused", 0) >= 1
    assert "pgvector" in response.answer.lower() or "apollo" in response.answer.lower()
