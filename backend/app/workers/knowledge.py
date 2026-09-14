"""
Phase 18 – Celery Knowledge Workers

Asynchronous background worker tasks for chunking transcripts, generating
embeddings, and indexing semantic passages into PostgreSQL pgvector and FTS.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.knowledge.chunking import SemanticChunker
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def execute_knowledge_indexing_task(self, tenant_id: str, meeting_id: str):
    """
    Background worker task executing semantic chunking and embedding indexing.
    Guarantees strict tenant isolation and citation persistence.
    """
    tenant_uuid = UUID(tenant_id)
    meeting_uuid = UUID(meeting_id)

    log = logger.bind(tenant_id=tenant_id, meeting_id=meeting_id)
    log.info("Starting knowledge indexing background task")

    db = SessionLocal()
    try:
        # 1. Enforce tenant ownership
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id == meeting_uuid, Meeting.tenant_id == tenant_uuid)
            .first()
        )
        if not meeting:
            raise ValueError("Meeting not found or tenant boundary violation.")

        # 2. Retrieve transcript
        transcript = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_uuid, Transcript.tenant_id == tenant_uuid)
            .first()
        )
        if not transcript:
            raise ValueError("Transcript not found for meeting.")

        segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.transcript_id == transcript.id)
            .order_by(TranscriptSegment.sequence_number.asc())
            .all()
        )
        if not segments:
            log.warn("Transcript has no segments to index.")
            return {"status": "SKIPPED", "chunks_created": 0}

        # 3. Clean previous chunks to ensure idempotency
        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.meeting_id == meeting_uuid,
            KnowledgeChunk.tenant_id == tenant_uuid,
        ).delete()
        db.flush()

        # 4. Semantic Chunking
        chunker = SemanticChunker()
        raw_chunks = chunker.chunk_segments(segments)

        # 5. Embeddings & Indexing
        gateway = EmbeddingGateway()
        provider = gateway.get_provider()

        for idx, rc in enumerate(raw_chunks):
            emb = provider.embed_text(rc.content)
            k_chunk = KnowledgeChunk(
                tenant_id=tenant_uuid,
                meeting_id=meeting_uuid,
                transcript_id=transcript.id,
                content=rc.content,
                chunk_index=idx,
                token_count=rc.token_count,
                primary_topic=rc.primary_topic,
                speaker_names=rc.speaker_names,
                start_seconds=rc.start_seconds,
                end_seconds=rc.end_seconds,
                embedding=emb,
            )
            db.add(k_chunk)
            db.flush()

            for seq, seg_id in enumerate(rc.segment_ids):
                db.add(
                    KnowledgeChunkSegment(
                        tenant_id=tenant_uuid,
                        chunk_id=k_chunk.id,
                        segment_id=seg_id,
                        sequence_in_chunk=seq,
                    )
                )

        db.commit()
        log.info("Knowledge indexing completed", chunks_created=len(raw_chunks))
        return {"status": "COMPLETED", "chunks_created": len(raw_chunks)}

    except Exception as exc:
        db.rollback()
        log.error("Knowledge indexing failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
