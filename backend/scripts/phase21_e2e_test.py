"""
Phase 21 – End-to-End Permission-Aware RAG Test
================================================

Validates complete Phase 21 deliverables:
  1. AuthorizedRetrievalScope domain model and SQL predicate encapsulation.
  2. AuthorizationService role-based resolution (ADMIN/MANAGER vs EMPLOYEE).
  3. Push-Down SQL Authorization in pgvector dense search before distance sorting.
  4. Push-Down SQL Authorization in PostgreSQL FTS keyword search before ranking.
  5. HybridRetriever execution with strict AuthorizedRetrievalScope.
  6. Citation IDOR Defense via AuthorizationService and REST API (GET /api/v1/chat/citations/{segment_id}).

Run with:
    python scripts/phase21_e2e_test.py
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

from app.auth.scope import AuthorizedRetrievalScope
from app.auth.service import AuthorizationService
from app.core.database import SessionLocal
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.retrieval.keyword import KeywordSearchEngine
from app.knowledge.retrieval.reranker import IdentityReranker
from app.knowledge.retrieval.retriever import HybridRetriever
from app.knowledge.retrieval.vector import VectorSearchEngine
from app.main import app
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user


def run_phase21_e2e_test():
    print("==================================================================")
    print("🚀 Starting Phase 21 (Permission-Aware RAG) E2E Test")
    print("==================================================================")

    db = SessionLocal()
    client = TestClient(app)

    try:
        uid = str(uuid.uuid4())[:8]
        # 1. Provision Multi-Tenant & Multi-User Architecture
        print("\n[Step 1] Provisioning Multi-Tenant Organizations, Users, and Roles...")
        org_a = Organization(name=f"Enterprise Alpha {uid}", slug=f"alpha-{uid}")
        org_b = Organization(name=f"Competitor Beta {uid}", slug=f"beta-{uid}")
        db.add_all([org_a, org_b])
        db.commit()

        # Users in Tenant Alpha:
        admin_a = User(email=f"admin_{uid}@alpha.com", password_hash="hash", full_name="Admin Alpha")
        emp_a1 = User(email=f"emp1_{uid}@alpha.com", password_hash="hash", full_name="Alice Engineer")
        emp_a2 = User(email=f"emp2_{uid}@alpha.com", password_hash="hash", full_name="Bob Sales")
        # User in Tenant Beta:
        user_b = User(email=f"user_{uid}@beta.com", password_hash="hash", full_name="Beta Director")
        db.add_all([admin_a, emp_a1, emp_a2, user_b])
        db.flush()

        # Meetings in Tenant Alpha
        meeting_public = Meeting(tenant_id=org_a.id, owner_id=emp_a1.id, title="Alpha Public Architecture Sync")
        meeting_confidential = Meeting(tenant_id=org_a.id, owner_id=emp_a2.id, title="Alpha Private Compensation Review")
        # Meeting in Tenant Beta
        meeting_beta = Meeting(tenant_id=org_b.id, owner_id=user_b.id, title="Beta Secret Project")
        db.add_all([meeting_public, meeting_confidential, meeting_beta])
        db.flush()

        # Media & Transcripts
        ma1 = MediaAsset(tenant_id=org_a.id, meeting_id=meeting_public.id, filename="m1.wav", original_content_type="audio/wav", status=MediaStatus.READY)
        ma2 = MediaAsset(tenant_id=org_a.id, meeting_id=meeting_confidential.id, filename="m2.wav", original_content_type="audio/wav", status=MediaStatus.READY)
        ma_b = MediaAsset(tenant_id=org_b.id, meeting_id=meeting_beta.id, filename="mb.wav", original_content_type="audio/wav", status=MediaStatus.READY)
        db.add_all([ma1, ma2, ma_b])
        db.flush()

        t1 = Transcript(tenant_id=org_a.id, meeting_id=meeting_public.id, media_asset_id=ma1.id, language="en", duration_seconds=180.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        t2 = Transcript(tenant_id=org_a.id, meeting_id=meeting_confidential.id, media_asset_id=ma2.id, language="en", duration_seconds=120.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        tb = Transcript(tenant_id=org_b.id, meeting_id=meeting_beta.id, media_asset_id=ma_b.id, language="en", duration_seconds=90.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        db.add_all([t1, t2, tb])
        db.flush()

        # Transcript Segments
        spk = Speaker(tenant_id=org_a.id, meeting_id=meeting_public.id, speaker_label="SPEAKER_00", display_name="Alice")
        db.add(spk)
        db.flush()

        seg1 = TranscriptSegment(
            tenant_id=org_a.id, transcript_id=t1.id, sequence_number=0, start_seconds=5.0, end_seconds=15.0,
            text="We are migrating our database tier to pgvector for scalable embedding search.", confidence=0.98, speaker_id=spk.id
        )
        seg2 = TranscriptSegment(
            tenant_id=org_a.id, transcript_id=t2.id, sequence_number=0, start_seconds=2.0, end_seconds=10.0,
            text="Executive bonuses for Q3 are approved at fifteen percent across leadership.", confidence=0.99
        )
        seg_b = TranscriptSegment(
            tenant_id=org_b.id, transcript_id=tb.id, sequence_number=0, start_seconds=1.0, end_seconds=8.0,
            text="Beta proprietary algorithm code name is OMEGA-NINE.", confidence=0.95
        )
        db.add_all([seg1, seg2, seg_b])
        db.flush()

        # Knowledge Chunks with Vector Embeddings
        gateway = EmbeddingGateway()
        vec1 = gateway.embed_text(seg1.text)
        vec2 = gateway.embed_text(seg2.text)
        vecb = gateway.embed_text(seg_b.text)

        chunk1 = KnowledgeChunk(
            tenant_id=org_a.id, meeting_id=meeting_public.id, transcript_id=t1.id,
            content=seg1.text, chunk_index=0, token_count=16, embedding=vec1, start_seconds=5.0, end_seconds=15.0
        )
        chunk2 = KnowledgeChunk(
            tenant_id=org_a.id, meeting_id=meeting_confidential.id, transcript_id=t2.id,
            content=seg2.text, chunk_index=0, token_count=14, embedding=vec2, start_seconds=2.0, end_seconds=10.0
        )
        chunk_b = KnowledgeChunk(
            tenant_id=org_b.id, meeting_id=meeting_beta.id, transcript_id=tb.id,
            content=seg_b.text, chunk_index=0, token_count=10, embedding=vecb, start_seconds=1.0, end_seconds=8.0
        )
        db.add_all([chunk1, chunk2, chunk_b])
        db.flush()

        # Junctions
        j1 = KnowledgeChunkSegment(tenant_id=org_a.id, chunk_id=chunk1.id, segment_id=seg1.id, sequence_in_chunk=0)
        j2 = KnowledgeChunkSegment(tenant_id=org_a.id, chunk_id=chunk2.id, segment_id=seg2.id, sequence_in_chunk=0)
        jb = KnowledgeChunkSegment(tenant_id=org_b.id, chunk_id=chunk_b.id, segment_id=seg_b.id, sequence_in_chunk=0)
        db.add_all([j1, j2, jb])
        db.commit()
        print("  ✓ Multi-tenant data and vector embeddings established.")

        # Step 2: Test AuthorizationService and AuthorizedRetrievalScope
        print("\n[Step 2] Testing AuthorizationService RBAC Scope Derivation...")
        auth_service = AuthorizationService(db=db)

        # ADMIN Scope
        admin_ctx = CurrentUserContext(user_id=admin_a.id, organization_id=org_a.id, role_code="ADMIN", permissions=["meetings:read"])
        admin_scope = auth_service.resolve_scope(admin_ctx)
        assert admin_scope.allowed_meeting_ids is None, "ADMIN must possess tenant-wide meeting access (None)"
        print(f"  ✓ Admin scope: tenant_wide={admin_scope.allowed_meeting_ids is None}")

        # EMPLOYEE (Alice) Scope - should only see her owned meeting (meeting_public)
        alice_ctx = CurrentUserContext(user_id=emp_a1.id, organization_id=org_a.id, role_code="EMPLOYEE", permissions=["meetings:read"])
        alice_scope = auth_service.resolve_scope(alice_ctx)
        assert alice_scope.allowed_meeting_ids == {meeting_public.id}, "Alice should only have access to meeting_public"
        print(f"  ✓ Alice restricted scope: allowed_meetings={len(alice_scope.allowed_meeting_ids)}")

        # Step 3: Push-Down SQL Authorization in pgvector
        print("\n[Step 3] Testing Push-Down SQL Authorization in VectorSearchEngine...")
        vector_engine = VectorSearchEngine(db=db, tenant_id=org_a.id)

        # Alice searches for "executive bonuses" (contained in confidential meeting she doesn't own)
        alice_results = vector_engine.search(
            query="executive bonuses",
            allowed_meeting_ids=alice_scope.allowed_meeting_ids
        )
        # None of Alice's results should come from meeting_confidential!
        assert all(chunk.meeting_id != meeting_confidential.id for chunk, _ in alice_results), (
            "Alice must NOT retrieve any chunks from confidential meeting"
        )
        # Zero permitted meetings should return exactly 0 results
        assert len(vector_engine.search(query="executive bonuses", allowed_meeting_ids=set())) == 0, (
            "Zero permitted meetings must yield 0 vector results"
        )
        print("  ✓ Alice blocked from confidential chunks in vector search via SQL push-down.")

        # Admin searches for "executive bonuses" -> allowed
        admin_results = vector_engine.search(
            query="executive bonuses",
            allowed_meeting_ids=admin_scope.allowed_meeting_ids
        )
        assert len(admin_results) >= 1, "Admin must successfully retrieve confidential chunks"
        print(f"  ✓ Admin retrieved {len(admin_results)} chunks.")

        # Step 4: Push-Down SQL Authorization in KeywordSearchEngine
        print("\n[Step 4] Testing Push-Down SQL Authorization in KeywordSearchEngine...")
        keyword_engine = KeywordSearchEngine(db=db, tenant_id=org_a.id)
        alice_kw_results = keyword_engine.search(
            query="bonuses",
            allowed_meeting_ids=alice_scope.allowed_meeting_ids
        )
        assert len(alice_kw_results) == 0, "Alice must NOT retrieve confidential FTS results"
        print("  ✓ Alice blocked from confidential chunks in FTS search.")

        # Step 5: HybridRetriever with AuthorizedRetrievalScope
        print("\n[Step 5] Testing HybridRetriever with AuthorizedRetrievalScope...")
        retriever_alice = HybridRetriever(db=db, tenant_id=org_a.id, reranker=IdentityReranker(), scope=alice_scope)
        alice_hybrid = retriever_alice.search(query="pgvector database tier")
        assert alice_hybrid.total_results >= 1, "Alice should find public architecture chunks"
        assert alice_hybrid.results[0].meeting_id == meeting_public.id
        print(f"  ✓ Alice hybrid search resolved {alice_hybrid.total_results} authorized results.")

        # Step 6: Citation IDOR Defense
        print("\n[Step 6] Testing Citation IDOR Defense via AuthorizationService...")
        # Alice cannot access citation in confidential meeting
        can_access_conf = auth_service.validate_citation_access(scope=alice_scope, segment_id=seg2.id)
        assert can_access_conf is False, "Alice must be denied access to seg2 (confidential meeting)"
        # Alice cannot access citation in competitor tenant
        can_access_beta = auth_service.validate_citation_access(scope=alice_scope, segment_id=seg_b.id)
        assert can_access_beta is False, "Alice must be denied access to seg_b (Tenant Beta)"
        # Alice can access her own meeting citation
        can_access_pub = auth_service.validate_citation_access(scope=alice_scope, segment_id=seg1.id)
        assert can_access_pub is True, "Alice must have access to seg1"
        print("  ✓ AuthorizationService accurately gates citation access.")

        # Step 7: REST API Citation Endpoint (GET /api/v1/chat/citations/{segment_id})
        print("\n[Step 7] Testing REST API Citation Endpoint (GET /api/v1/chat/citations/{segment_id})...")
        app.dependency_overrides[get_current_user] = lambda: alice_ctx

        # Alice requests confidential citation -> 403 Forbidden
        r403_intra = client.get(f"/api/v1/chat/citations/{seg2.id}")
        assert r403_intra.status_code == 403, f"Expected 403, got {r403_intra.status_code}"
        print("  ✓ HTTP 403 on intra-tenant citation IDOR attempt.")

        # Alice requests competitor citation -> 403 Forbidden
        r403_cross = client.get(f"/api/v1/chat/citations/{seg_b.id}")
        assert r403_cross.status_code == 403, f"Expected 403, got {r403_cross.status_code}"
        print("  ✓ HTTP 403 on cross-tenant citation IDOR attempt.")

        # Alice requests public citation -> 200 OK
        r200 = client.get(f"/api/v1/chat/citations/{seg1.id}")
        assert r200.status_code == 200, f"Expected 200, got {r200.status_code}"
        data = r200.json()
        assert data["segment_id"] == str(seg1.id)
        assert "pgvector" in data["text"]
        assert data["speaker_name"] == "Alice"
        print(f"  ✓ HTTP 200 on authorized citation access: {data['text']}")

        app.dependency_overrides.clear()

        print("\n==================================================================")
        print("✅ PHASE 21 (Permission-Aware RAG) E2E TEST PASSED")
        print("==================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_phase21_e2e_test()
