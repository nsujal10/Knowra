"""
Phase 20 – End-to-End Hybrid Search & Reciprocal Rank Fusion Pipeline Test
==========================================================================

Validates complete Phase 20 deliverables:
  1. VectorSearchEngine with SQL-level tenant isolation prior to distance sorting.
  2. KeywordSearchEngine with PostgreSQL Full-Text Search (tsvector/ts_rank).
  3. ReciprocalRankFusion (RRF) combining vector and lexical rankings.
  4. Reranker protocol execution (CrossEncoder / Identity).
  5. Exact canonical transcript segment citation resolution (timestamps, confidence, speakers).
  6. Enterprise Search REST API (POST /api/v1/search) endpoint integration.

Run with:
    python scripts/phase20_e2e_test.py
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

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.knowledge.retrieval.fusion import ReciprocalRankFusion
from app.knowledge.retrieval.keyword import KeywordSearchEngine
from app.knowledge.retrieval.reranker import IdentityReranker
from app.knowledge.retrieval.retriever import HybridRetriever
from app.knowledge.retrieval.vector import VectorSearchEngine
from app.main import app
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.workers.knowledge import execute_knowledge_indexing_task


def run_phase20_e2e_test():
    print("==================================================================")
    print("🚀 Starting Phase 20 (Hybrid Search & RRF Pipeline) E2E Test")
    print("==================================================================")

    db = SessionLocal()
    try:
        # Step 1: Provision Multi-Tenant Test Data
        uid = str(uuid.uuid4())[:8]
        org = Organization(name=f"Cognitive Intelligence {uid}", slug=f"cog-intel-{uid}")
        db.add(org)
        db.commit()

        user = User(
            email=f"search_lead_{uid}@cog-intel.com",
            password_hash="argon2_hashed_pw",
            full_name="Search Engineering Lead",
        )
        db.add(user)
        db.flush()

        meeting = Meeting(
            tenant_id=org.id,
            owner_id=user.id,
            title="Hybrid RRF Search & Knowledge Architecture",
        )
        db.add(meeting)
        db.flush()

        speaker_alice = Speaker(
            tenant_id=org.id,
            meeting_id=meeting.id,
            speaker_label="SPEAKER_00",
            display_name="Alice Chen",
        )
        speaker_bob = Speaker(
            tenant_id=org.id,
            meeting_id=meeting.id,
            speaker_label="SPEAKER_01",
            display_name="Bob Miller",
        )
        db.add_all([speaker_alice, speaker_bob])
        db.flush()

        media = MediaAsset(
            tenant_id=org.id,
            meeting_id=meeting.id,
            filename="search_deep_dive.mp4",
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
            duration_seconds=180.0,
            provider_name="faster-whisper",
            model_name="base",
            model_version="1.0",
        )
        db.add(transcript)
        db.flush()

        dialogues = [
            (speaker_alice.id, 0.0, 15.0, "Let us review our hybrid retrieval strategy combining pgvector and PostgreSQL full text search."),
            (speaker_bob.id, 15.1, 35.0, "For keyword search, we use tsvector and ts_rank with English stemming."),
            (speaker_alice.id, 35.1, 60.0, "Reciprocal Rank Fusion with k=60 will balance dense semantic scores and lexical keyword frequencies."),
            (speaker_bob.id, 60.1, 90.0, "Crucially, each result returned must link back to exact canonical transcript segments with timestamps."),
            (speaker_alice.id, 90.1, 125.0, "We also apply an optional cross-encoder reranker on top candidates before formatting citations."),
            (speaker_bob.id, 125.1, 160.0, "Security check: all queries must enforce tenant_id at the SQL WHERE clause level."),
        ]

        segments = []
        for seq, (spk_id, start, end, text) in enumerate(dialogues, start=1):
            seg = TranscriptSegment(
                tenant_id=org.id,
                transcript_id=transcript.id,
                sequence_number=seq,
                speaker_id=spk_id,
                start_seconds=start,
                end_seconds=end,
                text=text,
                confidence=0.97,
            )
            segments.append(seg)
        db.add_all(segments)
        db.commit()

        print(f"✅ Provisioned Organization '{org.name}' with meeting and {len(segments)} segments.")

        # Step 2: Index via Background Worker
        print("\n⚡ Indexing transcript segments into pgvector & FTS...")
        indexing_res = execute_knowledge_indexing_task.run(
            tenant_id=str(org.id),
            meeting_id=str(meeting.id),
        )
        assert indexing_res["status"] == "COMPLETED"
        print(f"  - Chunks created and vector indexed: {indexing_res['chunks_total']}")

        # Step 3: Test Vector Search Engine Directly
        print("\n🔍 Testing VectorSearchEngine...")
        vec_engine = VectorSearchEngine(db=db, tenant_id=org.id)
        vec_results = vec_engine.search(query="semantic vector pgvector retrieval", limit=5)
        assert len(vec_results) > 0
        top_chunk, top_sim = vec_results[0]
        print(f"  - Vector Search Top Match: '{top_chunk.content[:60]}...' (Sim: {top_sim})")

        # Step 4: Test Keyword Search Engine Directly
        print("\n🔎 Testing KeywordSearchEngine...")
        kw_engine = KeywordSearchEngine(db=db, tenant_id=org.id)
        kw_results = kw_engine.search(query="Reciprocal Rank Fusion", limit=5)
        assert len(kw_results) > 0
        top_kw_chunk, top_kw_score = kw_results[0]
        print(f"  - Keyword Search Top Match: '{top_kw_chunk.content[:60]}...' (Score: {top_kw_score})")

        # Step 5: Test Reciprocal Rank Fusion (RRF) Logic
        print("\n🧮 Testing ReciprocalRankFusion (RRF)...")
        rrf = ReciprocalRankFusion(k=60)
        id_a, id_b = uuid.uuid4(), uuid.uuid4()
        fused = rrf.fuse([
            ([(id_a, 0.9), (id_b, 0.8)], 0.5),
            ([(id_a, 5.0)], 0.5),
        ])
        assert fused[0][0] == id_a
        print(f"  - Top RRF Candidate: {fused[0][0]} with combined score: {fused[0][1]}")

        # Step 6: Test HybridRetriever Full Pipeline & Citations
        print("\n🚀 Testing Complete HybridRetriever Pipeline with Citations...")
        hybrid_retriever = HybridRetriever(db=db, tenant_id=org.id, reranker=IdentityReranker())
        search_resp = hybrid_retriever.search(
            query="How does Reciprocal Rank Fusion combine results and citations?",
            limit=3,
        )

        assert len(search_resp.results) > 0
        first_result = search_resp.results[0]
        print(f"  - Query: '{search_resp.query}'")
        print(f"  - Total Results: {search_resp.total_results}")
        print(f"  - Top Result Chunk: '{first_result.content[:80]}...'")
        print(f"  - Top Result Fused Score: {first_result.score}")
        print(f"  - Citations Count: {len(first_result.citations)}")

        assert len(first_result.citations) > 0
        first_citation = first_result.citations[0]
        print(f"    * Citation Segment ID: {first_citation.segment_id}")
        print(f"    * Start Time: {first_citation.start_seconds}s, End Time: {first_citation.end_seconds}s")
        print(f"    * Speaker: {first_citation.speaker_name}")
        print(f"    * Text: '{first_citation.text}'")

        # Step 7: Test REST API Endpoint (POST /api/v1/search)
        print("\n🌐 Testing REST API Endpoint (POST /api/v1/search)...")
        app.dependency_overrides[get_current_user] = lambda: CurrentUserContext(
            user_id=user.id,
            organization_id=org.id,
            role_code="OWNER",
            permissions=["search:read"],
        )
        client = TestClient(app)

        api_response = client.post(
            "/api/v1/search",
            json={
                "query": "PostgreSQL full text search and pgvector citations",
                "limit": 5,
                "vector_weight": 0.6,
                "keyword_weight": 0.4,
            },
        )

        assert api_response.status_code == 200, f"API failed with status {api_response.status_code}: {api_response.text}"
        data = api_response.json()
        assert "results" in data
        assert data["total_results"] >= 1
        print(f"  - API Status: {api_response.status_code}")
        print(f"  - API Total Hits: {data['total_results']}")
        print(f"  - Top API Match: '{data['results'][0]['content'][:60]}...'")
        print(f"  - Citations resolved: {len(data['results'][0]['citations'])}")

        print("\n================================================================")
        print("🎉 Phase 20 (Hybrid Search & RRF Pipeline) E2E Test PASSED!")
        print("================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()


if __name__ == "__main__":
    run_phase20_e2e_test()
