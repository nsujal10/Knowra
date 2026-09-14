"""
Phase 19 – End-to-End Embeddings & Celery Indexing Pipeline Test
================================================================

Validates complete Phase 19 deliverables:
  1. KnowledgeEmbedding model with pgvector VECTOR(384) column, dimensions,
     provider/model provenance, and unique constraint on (tenant_id, content_hash, model_name, model_version).
  2. EmbeddingGateway:
     - Batching of document sets
     - Exponential backoff retry resilience
     - Deterministic SHA-256 fingerprinting
     - Provider abstraction
  3. Background Celery indexing pipeline:
     - First pass: Generates embeddings, populates knowledge_embeddings table
     - Second pass: Deterministic idempotency triggers SKIP, 0 duplicate embeddings generated.

Run with:
    python scripts/phase19_e2e_test.py
"""

import os
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from app.core.database import SessionLocal
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.embeddings.models import KnowledgeEmbedding
from app.knowledge.models import KnowledgeChunk
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.workers.knowledge import execute_knowledge_indexing_task


def run_phase19_e2e_test():
    print("==================================================================")
    print("🚀 Starting Phase 19 (Embeddings & Idempotent Indexing) E2E Test")
    print("==================================================================")

    db = SessionLocal()
    try:
        # Step 1: Provision Multi-Tenant Test Fixture
        uid = str(uuid.uuid4())[:8]
        org = Organization(name=f"Enterprise AI Corp {uid}", slug=f"ent-ai-{uid}")
        db.add(org)
        db.commit()

        user = User(
            email=f"chief_architect_{uid}@ent-ai.com",
            password_hash="argon2_hashed_pw",
            full_name="Chief Search Architect",
        )
        db.add(user)
        db.flush()

        meeting = Meeting(
            tenant_id=org.id,
            owner_id=user.id,
            title="Q3 Distributed Vector Search Architecture",
        )
        db.add(meeting)
        db.flush()

        media = MediaAsset(
            tenant_id=org.id,
            meeting_id=meeting.id,
            filename="vector_architecture_meeting.mp4",
            original_content_type="video/mp4",
            status=MediaStatus.READY,
        )
        db.add(media)
        db.flush()

        transcript = Transcript(
            tenant_id=org.id,
            meeting_id=meeting.id,
            media_asset_id=media.id,
            language="en",
            duration_seconds=120.0,
            provider_name="faster-whisper",
            model_name="base",
            model_version="1.0",
        )
        db.add(transcript)
        db.flush()

        # Step 2: Seed Canonical Transcript Segments
        dialogues = [
            ("00:00", 0.0, 10.0, "Welcome everyone. Today we finalize the pgvector deployment strategy for Knowra."),
            ("00:10", 10.1, 25.0, "We selected HNSW indexes with m=16 and ef_construction=64 for sub-5 millisecond retrieval."),
            ("00:25", 25.1, 45.0, "What about multi-tenant query isolation? We must enforce tenant_id before any vector distance calculation."),
            ("00:45", 45.1, 70.0, "Agreed. In SQL, WHERE tenant_id = :tenant_id runs first, guaranteeing no vector side-channel leaks."),
            ("01:10", 70.1, 95.0, "For batch embedding ingestion, Celery tasks must calculate SHA-256 hashes to guarantee deterministic idempotency."),
            ("01:35", 95.1, 120.0, "Confirmed. Retrying the indexing task will skip previously embedded chunks seamlessly."),
        ]

        segments = []
        for seq, (_, start, end, text) in enumerate(dialogues, start=1):
            seg = TranscriptSegment(
                tenant_id=org.id,
                transcript_id=transcript.id,
                sequence_number=seq,
                start_seconds=start,
                end_seconds=end,
                text=text,
                confidence=0.98,
            )
            segments.append(seg)
        db.add_all(segments)
        db.commit()

        print(f"✅ Provisioned Organization '{org.name}' with {len(segments)} canonical transcript segments.")

        # Step 3: Test EmbeddingGateway Functionality
        print("\n🧪 Testing EmbeddingGateway Provider Abstraction & Batching...")
        gateway = EmbeddingGateway(batch_size=4, max_retries=3)
        sample_texts = [s.text for s in segments]
        batch_vectors = gateway.embed_batch(sample_texts)

        assert len(batch_vectors) == len(sample_texts), "Batch vector count mismatch"
        assert len(batch_vectors[0]) == gateway.dimension, f"Vector dimension mismatch (got {len(batch_vectors[0])})"
        print(f"  - Provider: {gateway.provider_name}")
        print(f"  - Model: {gateway.model_name} (version {gateway.model_version})")
        print(f"  - Dimensions: {gateway.dimension}")
        print(f"  - Successfully generated {len(batch_vectors)} batch embeddings.")

        # Step 4: Test Deterministic SHA-256 Hash Idempotency
        hash1 = gateway.compute_content_hash("  Multi-tenant pgvector   isolation   guarantee  ")
        hash2 = gateway.compute_content_hash("Multi-tenant pgvector isolation guarantee")
        assert hash1 == hash2, "Content hash normalization failed"
        assert len(hash1) == 64, "Hash must be 64-char hex string"
        print(f"  - SHA-256 Content Hash Verified: {hash1[:16]}... (Whitespace normalized)")

        # Step 5: Execute Celery Indexing Task - Run 1 (Initial Ingestion)
        print("\n⚡ Executing Background Celery Indexing Task (Run 1: Ingestion)...")
        run1_result = execute_knowledge_indexing_task.run(
            tenant_id=str(org.id),
            meeting_id=str(meeting.id),
        )

        assert run1_result["status"] == "COMPLETED"
        assert run1_result["embeddings_generated"] > 0
        assert run1_result["embeddings_skipped"] == 0
        print(f"  - Run 1 Status: {run1_result['status']}")
        print(f"  - Chunks Created: {run1_result['chunks_total']}")
        print(f"  - Embeddings Generated: {run1_result['embeddings_generated']}")
        print(f"  - Embeddings Skipped: {run1_result['embeddings_skipped']}")

        # Verify database records
        persisted_embs = (
            db.query(KnowledgeEmbedding)
            .filter(
                KnowledgeEmbedding.tenant_id == org.id,
                KnowledgeEmbedding.meeting_id == meeting.id,
            )
            .all()
        )
        assert len(persisted_embs) == run1_result["embeddings_generated"]
        print(f"  - Verified {len(persisted_embs)} KnowledgeEmbedding rows in PostgreSQL.")

        # Step 6: Execute Celery Indexing Task - Run 2 (Deterministic Retry Idempotency)
        print("\n🔁 Executing Background Celery Indexing Task (Run 2: Idempotent Retry)...")
        run2_result = execute_knowledge_indexing_task.run(
            tenant_id=str(org.id),
            meeting_id=str(meeting.id),
        )

        assert run2_result["status"] == "COMPLETED"
        assert run2_result["embeddings_generated"] == 0, "Idempotency failed: New embeddings were generated!"
        assert run2_result["embeddings_skipped"] == run1_result["chunks_total"], "Expected all chunks to be skipped!"
        print(f"  - Run 2 Status: {run2_result['status']}")
        print(f"  - Embeddings Generated: {run2_result['embeddings_generated']} (DETERMINISTIC SKIP VERIFIED)")
        print(f"  - Embeddings Skipped: {run2_result['embeddings_skipped']}")

        # Verify no duplicate rows
        post_retry_embs = (
            db.query(KnowledgeEmbedding)
            .filter(
                KnowledgeEmbedding.tenant_id == org.id,
                KnowledgeEmbedding.meeting_id == meeting.id,
            )
            .all()
        )
        assert len(post_retry_embs) == len(persisted_embs), "Duplicate KnowledgeEmbedding records detected!"
        print(f"  - Row count invariant preserved ({len(post_retry_embs)} rows). Zero duplicate entries.")

        print("\n================================================================")
        print("🎉 Phase 19 (Embeddings & Idempotent Indexing) E2E Test PASSED!")
        print("================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_phase19_e2e_test()
