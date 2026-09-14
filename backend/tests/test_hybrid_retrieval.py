"""
Unit & Integration Tests: Phase 18 Hybrid Retrieval Fusion & Citation Resolution
Validates:
  - Fusion and reranking of keyword and vector search results (RRF)
  - Citation resolution mapping back to canonical TranscriptSegment timestamps
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.retrieval import HybridRetrievalService
from app.models.media_asset import MediaAsset
from app.models.enums import MediaStatus
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_hybrid_retrieval_rrf_and_citations(db_session):
    uid = str(uuid.uuid4())[:6]
    org = Organization(name=f"Hybrid Test Org {uid}", slug=f"hybrid-org-{uid}")
    db_session.add(org)
    db_session.commit()

    user = User(email=f"hybrid_{uid}@example.com", password_hash="hash", full_name="Hybrid User")
    db_session.add(user)
    db_session.flush()

    meeting = Meeting(tenant_id=org.id, owner_id=user.id, title="Engineering All-Hands")
    db_session.add(meeting)
    db_session.commit()

    media = MediaAsset(
        tenant_id=org.id,
        meeting_id=meeting.id,
        filename="meeting_audio.wav",
        original_content_type="audio/wav",
        status=MediaStatus.READY,
    )
    db_session.add(media)
    db_session.flush()

    transcript = Transcript(
        tenant_id=org.id,
        meeting_id=meeting.id,
        media_asset_id=media.id,
        language="en",
        duration_seconds=60.0,
        provider_name="test",
        model_name="test",
        model_version="1.0",
    )
    db_session.add(transcript)
    db_session.commit()

    # 1. Create canonical transcript segments
    seg1 = TranscriptSegment(
        tenant_id=org.id,
        transcript_id=transcript.id,
        sequence_number=1,
        start_seconds=10.0,
        end_seconds=15.5,
        text="We are standardizing our microservices communication on gRPC protocols.",
        confidence=0.98,
    )
    seg2 = TranscriptSegment(
        tenant_id=org.id,
        transcript_id=transcript.id,
        sequence_number=2,
        start_seconds=15.5,
        end_seconds=22.0,
        text="This reduces JSON serialization overhead and provides strict protobuf schemas.",
        confidence=0.95,
    )
    db_session.add_all([seg1, seg2])
    db_session.commit()

    # 2. Create knowledge chunk linked to these segments
    gateway = EmbeddingGateway()
    provider = gateway.get_provider()

    chunk_content = f"{seg1.text}\n{seg2.text}"
    chunk = KnowledgeChunk(
        tenant_id=org.id,
        meeting_id=meeting.id,
        transcript_id=transcript.id,
        content=chunk_content,
        start_seconds=10.0,
        end_seconds=22.0,
        token_count=20,
        embedding=provider.embed_text(chunk_content),
    )
    db_session.add(chunk)
    db_session.flush()

    # Link segments for citation resolution
    db_session.add(KnowledgeChunkSegment(tenant_id=org.id, chunk_id=chunk.id, segment_id=seg1.id, sequence_in_chunk=0))
    db_session.add(KnowledgeChunkSegment(tenant_id=org.id, chunk_id=chunk.id, segment_id=seg2.id, sequence_in_chunk=1))
    db_session.commit()

    # 3. Perform Hybrid Search
    retrieval_service = HybridRetrievalService(db=db_session, tenant_id=org.id)
    res = retrieval_service.hybrid_search(query="gRPC protobuf serialization", limit=3)

    assert res.total_results >= 1
    top_hit = res.results[0]
    assert top_hit.chunk_id == chunk.id
    assert top_hit.score > 0.0

    # 4. Verify Citation Resolution
    assert len(top_hit.citations) == 2
    cit1 = top_hit.citations[0]
    assert cit1.segment_id == seg1.id
    assert cit1.start_seconds == 10.0
    assert "gRPC" in cit1.text

    cit2 = top_hit.citations[1]
    assert cit2.segment_id == seg2.id
    assert cit2.start_seconds == 15.5
    assert "JSON" in cit2.text
