"""
Phase 18 – End-to-End Knowledge Chunking, Embedding & Hybrid Search Test
========================================================================

Validates complete Phase 18 pipeline:
  1. Canonical Transcript Segments Generation
  2. Semantic Conversation Chunking (Turn-aware & boundary-aware)
  3. pgvector Vector(384) Embedding Generation & Indexing
  4. PostgreSQL Full-Text Search (TSVECTOR)
  5. Reciprocal Rank Fusion (RRF) Hybrid Retrieval
  6. Exact Transcript Segment Citation Resolution (Video Timeline timestamps)
  7. Strict Multi-Tenant Isolation Protection

Run with:
    python scripts/phase18_e2e_test.py
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
from app.knowledge.chunking import SemanticChunker
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.retrieval import HybridRetrievalService
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User


def run_phase18_e2e_test():
    print("================================================================")
    print("🚀 Starting Phase 18 (Knowledge Chunking & Hybrid Search) E2E Test")
    print("================================================================")

    db = SessionLocal()
    try:
        # Step 1: Provision Primary Tenant
        uid = str(uuid.uuid4())[:8]
        org = Organization(name=f"Cognitive Systems {uid}", slug=f"cog-sys-{uid}")
        db.add(org)
        db.flush()

        user = User(
            email=f"nlp_engineer_{uid}@cogsys.com",
            password_hash="hash_pw",
            full_name="NLP Engineer",
        )
        db.add(user)
        db.flush()

        meeting = Meeting(tenant_id=org.id, owner_id=user.id, title="Customer Intelligence Engine Review")
        db.add(meeting)
        db.flush()

        media = MediaAsset(
            tenant_id=org.id,
            meeting_id=meeting.id,
            filename="meeting_call.mp4",
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
            provider_name="whisper",
            model_name="large-v3",
            model_version="1.0",
        )
        db.add(transcript)
        db.flush()

        # Add Speakers
        spk_david = Speaker(tenant_id=org.id, meeting_id=meeting.id, speaker_label="SPEAKER_00", display_name="David")
        spk_zira = Speaker(tenant_id=org.id, meeting_id=meeting.id, speaker_label="SPEAKER_01", display_name="Zira")
        db.add_all([spk_david, spk_zira])
        db.flush()

        # Step 2: Create Canonical Dialogue Turns
        seg1 = TranscriptSegment(
            tenant_id=org.id,
            transcript_id=transcript.id,
            sequence_number=1,
            speaker_id=spk_david.id,
            start_seconds=0.0,
            end_seconds=4.37,
            text="Good morning team, let us review our customer intelligence engine benchmarks.",
            confidence=0.98,
        )
        seg2 = TranscriptSegment(
            tenant_id=org.id,
            transcript_id=transcript.id,
            sequence_number=2,
            speaker_id=spk_zira.id,
            start_seconds=4.37,
            end_seconds=9.29,
            text="Thank you David, the integration pipeline latency is under fifty milliseconds on GPU.",
            confidence=0.96,
        )
        seg3 = TranscriptSegment(
            tenant_id=org.id,
            transcript_id=transcript.id,
            sequence_number=3,
            speaker_id=spk_david.id,
            start_seconds=9.29,
            end_seconds=15.0,
            text="Excellent, we will deploy pgvector for semantic search across our enterprise knowledge base.",
            confidence=0.97,
        )
        db.add_all([seg1, seg2, seg3])
        db.commit()

        print(f"✅ Provisioned Meeting with {3} canonical segments for David & Zira")

        # Step 3: Semantic Conversation Chunking
        chunker = SemanticChunker(target_token_min=10, target_token_max=150)
        segments = [seg1, seg2, seg3]
        raw_chunks = chunker.chunk_segments(segments)
        assert len(raw_chunks) >= 1
        print(f"✅ Semantic Chunking produced {len(raw_chunks)} cohesive passages")

        # Step 4: Generate Embeddings & Index into PostgreSQL (pgvector)
        gateway = EmbeddingGateway()
        provider = gateway.get_provider()

        for idx, rc in enumerate(raw_chunks):
            vector = provider.embed_text(rc.content)
            k_chunk = KnowledgeChunk(
                tenant_id=org.id,
                meeting_id=meeting.id,
                transcript_id=transcript.id,
                content=rc.content,
                chunk_index=idx,
                token_count=rc.token_count,
                primary_topic=rc.primary_topic,
                speaker_names=rc.speaker_names,
                start_seconds=rc.start_seconds,
                end_seconds=rc.end_seconds,
                embedding=vector,
            )
            db.add(k_chunk)
            db.flush()

            for seq, s_id in enumerate(rc.segment_ids):
                db.add(
                    KnowledgeChunkSegment(
                        tenant_id=org.id,
                        chunk_id=k_chunk.id,
                        segment_id=s_id,
                        sequence_in_chunk=seq,
                    )
                )

        db.commit()
        print(f"✅ Indexed {len(raw_chunks)} chunks with 384-dim pgvector embeddings and citation links")

        # Step 5: Execute Hybrid Retrieval (Vector + Keyword + RRF)
        retrieval_service = HybridRetrievalService(db=db, tenant_id=org.id)
        query = "pgvector semantic search latency"
        search_res = retrieval_service.hybrid_search(query=query, limit=3)

        assert search_res.total_results >= 1, "Expected at least 1 hybrid search hit"
        top_match = search_res.results[0]
        print(f"✅ Hybrid Search hit for '{query}': Score={top_match.score:.4f}, Vector Rank={top_match.vector_rank}")

        # Step 6: Verify Exact Citations
        assert len(top_match.citations) >= 1
        print(f"✅ Resolved {len(top_match.citations)} Citations:")
        for c in top_match.citations:
            print(f"   • [{c.start_seconds:.2f}s - {c.end_seconds:.2f}s] {c.speaker_name}: {c.text[:50]}...")

        # Step 7: Enforce Multi-Tenant Isolation
        other_uid = str(uuid.uuid4())[:8]
        other_org = Organization(name=f"Foreign Corp {other_uid}", slug=f"foreign-{other_uid}")
        db.add(other_org)
        db.commit()

        foreign_service = HybridRetrievalService(db=db, tenant_id=other_org.id)
        foreign_res = foreign_service.hybrid_search(query=query, limit=5)
        assert foreign_res.total_results == 0, "Cross-tenant leak: Foreign tenant retrieved cognitive chunks!"
        print("🔒 Multi-Tenant Boundary Verified: Foreign tenant cannot access knowledge chunks.")

        print("================================================================")
        print("🎉 Phase 18 E2E Knowledge Chunking & Hybrid Search PASSED!")
        print("================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_phase18_e2e_test()
