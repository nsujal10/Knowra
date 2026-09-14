"""
Phase 19 – Celery Knowledge Workers (Batching & Deterministic Idempotency)

Asynchronous tasks for chunking transcripts, generating batch embeddings with
exponential backoff, and indexing into pgvector with SHA-256 deduplication.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.knowledge.chunking import SemanticChunker
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.embeddings.models import KnowledgeEmbedding
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def execute_knowledge_indexing_task(self, tenant_id: str, meeting_id: str):
    """
    Background worker task executing semantic chunking, batch embedding generation,
    and pgvector indexing with deterministic SHA-256 idempotency.
    """
    tenant_uuid = UUID(tenant_id)
    meeting_uuid = UUID(meeting_id)

    log = logger.bind(tenant_id=tenant_id, meeting_id=meeting_id)
    log.info("Starting knowledge indexing background task with idempotency checks")

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
            return {"status": "SKIPPED", "reason": "NO_SEGMENTS", "chunks_created": 0}

        # 3. Semantic Conversation Chunking
        chunker = SemanticChunker()
        raw_chunks = chunker.chunk_segments(segments)
        if not raw_chunks:
            return {"status": "SKIPPED", "reason": "NO_CHUNKS", "chunks_created": 0}

        gateway = EmbeddingGateway(batch_size=16, max_retries=3)
        model_name = getattr(settings, "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        provider_name = getattr(settings, "EMBEDDING_PROVIDER", "deterministic")
        model_version = "1.0"

        # Check existing chunks for this meeting
        existing_chunks = (
            db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.meeting_id == meeting_uuid,
                KnowledgeChunk.tenant_id == tenant_uuid,
            )
            .all()
        )
        existing_by_idx = {c.chunk_index: c for c in existing_chunks}

        chunks_created = 0
        embeddings_generated = 0
        embeddings_skipped = 0

        # Extract texts needing embedding
        texts_to_embed = []
        chunk_targets = []

        for idx, rc in enumerate(raw_chunks):
            content_hash = gateway.compute_content_hash(rc.content)

            # Check if embedding already exists by (tenant_id, content_hash, model_name, model_version)
            existing_emb = (
                db.query(KnowledgeEmbedding)
                .filter(
                    KnowledgeEmbedding.tenant_id == tenant_uuid,
                    KnowledgeEmbedding.content_hash == content_hash,
                    KnowledgeEmbedding.model_name == model_name,
                    KnowledgeEmbedding.model_version == model_version,
                )
                .first()
            )

            # Locate or create chunk
            if idx in existing_by_idx:
                k_chunk = existing_by_idx[idx]
                k_chunk.content = rc.content
                k_chunk.token_count = rc.token_count
                k_chunk.start_seconds = rc.start_seconds
                k_chunk.end_seconds = rc.end_seconds
            else:
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
                )
                db.add(k_chunk)
                db.flush()
                chunks_created += 1

                # Link segments
                for seq, s_id in enumerate(rc.segment_ids):
                    db.add(
                        KnowledgeChunkSegment(
                            tenant_id=tenant_uuid,
                            chunk_id=k_chunk.id,
                            segment_id=s_id,
                            sequence_in_chunk=seq,
                        )
                    )

            if existing_emb:
                # Idempotent skip! Reuse existing vector
                k_chunk.embedding = existing_emb.embedding
                embeddings_skipped += 1
                log.info("Skipped embedding generation due to content_hash match", content_hash=content_hash)
            else:
                texts_to_embed.append(rc.content)
                chunk_targets.append((k_chunk, content_hash))

        # Batch embed any pending texts
        if texts_to_embed:
            batch_vectors = gateway.embed_batch(texts_to_embed)
            for (k_chunk, c_hash), vec in zip(chunk_targets, batch_vectors):
                k_chunk.embedding = vec
                emb_record = KnowledgeEmbedding(
                    tenant_id=tenant_uuid,
                    chunk_id=k_chunk.id,
                    meeting_id=meeting_uuid,
                    content_hash=c_hash,
                    provider_name=provider_name,
                    model_name=model_name,
                    model_version=model_version,
                    dimensions=len(vec),
                    embedding=vec,
                )
                db.add(emb_record)
                embeddings_generated += 1

        db.commit()
        log.info(
            "Knowledge indexing completed successfully",
            chunks_total=len(raw_chunks),
            embeddings_generated=embeddings_generated,
            embeddings_skipped=embeddings_skipped,
        )
        return {
            "status": "COMPLETED",
            "chunks_total": len(raw_chunks),
            "embeddings_generated": embeddings_generated,
            "embeddings_skipped": embeddings_skipped,
        }

    except Exception as exc:
        db.rollback()
        log.error("Knowledge indexing task failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
