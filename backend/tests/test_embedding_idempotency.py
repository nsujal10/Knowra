"""
Integration Test: Embedding Idempotency (Phase 19)
Proves that a Celery task re-run / retry on a processed chunk yields a SKIP
operation based on the SHA-256 content_hash.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.embeddings.models import KnowledgeEmbedding
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.workers.knowledge import execute_knowledge_indexing_task


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_embedding_idempotency_skips_processed_chunks(db_session):
    run_id = str(uuid.uuid4())[:8]
    org = Organization(name=f"Idempotency Org {run_id}", slug=f"idemp-org-{run_id}")
    db_session.add(org)
    db_session.commit()

    user = User(email=f"idemp_{run_id}@example.com", password_hash="hash", full_name="Idemp User")
    db_session.add(user)
    db_session.flush()

    meeting = Meeting(tenant_id=org.id, owner_id=user.id, title=f"Idempotency Meeting {run_id}")
    db_session.add(meeting)
    db_session.flush()

    media = MediaAsset(
        tenant_id=org.id,
        meeting_id=meeting.id,
        filename="test.wav",
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
        duration_seconds=18.0,
        provider_name="faster-whisper",
        model_name="base",
        model_version="1.0",
    )
    db_session.add(transcript)
    db_session.flush()

    # Add realistic dialogue segments
    seg1 = TranscriptSegment(
        tenant_id=org.id,
        transcript_id=transcript.id,
        sequence_number=1,
        text="Welcome team, let us review the database sharding migration schedule for Q4.",
        start_seconds=0.0,
        end_seconds=5.0,
        confidence=0.98,
    )
    seg2 = TranscriptSegment(
        tenant_id=org.id,
        transcript_id=transcript.id,
        sequence_number=2,
        text="We tested pgvector performance with HNSW indexes and query latency is under 5 milliseconds.",
        start_seconds=5.1,
        end_seconds=12.0,
        confidence=0.95,
    )
    seg3 = TranscriptSegment(
        tenant_id=org.id,
        transcript_id=transcript.id,
        sequence_number=3,
        text="Excellent work. We will proceed with the rollout on October 15th.",
        start_seconds=12.5,
        end_seconds=18.0,
        confidence=0.99,
    )
    db_session.add_all([seg1, seg2, seg3])
    db_session.commit()

    # --- Run 1: Initial Ingestion ---
    # Call the Celery task function directly
    result_run1 = execute_knowledge_indexing_task.run(
        tenant_id=str(org.id),
        meeting_id=str(meeting.id),
    )

    assert result_run1["status"] == "COMPLETED"
    assert result_run1["chunks_total"] >= 1
    assert result_run1["embeddings_generated"] >= 1
    assert result_run1["embeddings_skipped"] == 0

    # Verify embeddings exist in database
    initial_embs = (
        db_session.query(KnowledgeEmbedding)
        .filter(KnowledgeEmbedding.tenant_id == org.id, KnowledgeEmbedding.meeting_id == meeting.id)
        .all()
    )
    initial_count = len(initial_embs)
    assert initial_count >= 1

    gateway = EmbeddingGateway()
    for emb in initial_embs:
        assert emb.content_hash is not None
        assert len(emb.content_hash) == 64  # SHA-256 hex string

    # --- Run 2: Re-run / Retry Task (Identical Data) ---
    result_run2 = execute_knowledge_indexing_task.run(
        tenant_id=str(org.id),
        meeting_id=str(meeting.id),
    )

    assert result_run2["status"] == "COMPLETED"
    assert result_run2["chunks_total"] == result_run1["chunks_total"]
    # All embeddings MUST be skipped due to SHA-256 content_hash match!
    assert result_run2["embeddings_generated"] == 0
    assert result_run2["embeddings_skipped"] == result_run1["chunks_total"]

    # Verify that no duplicate embedding rows were inserted
    after_retry_embs = (
        db_session.query(KnowledgeEmbedding)
        .filter(KnowledgeEmbedding.tenant_id == org.id, KnowledgeEmbedding.meeting_id == meeting.id)
        .all()
    )
    assert len(after_retry_embs) == initial_count, "Duplicate embeddings were inserted on retry!"
