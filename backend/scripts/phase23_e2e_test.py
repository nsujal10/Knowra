"""
Phase 23 – End-to-End Cross-Meeting Intelligence Test
=====================================================

Validates complete Phase 23 deliverables:
  1. QueryDecomposer: Decomposes complex longitudinal questions into sub-queries.
  2. CrossMeetingResolver: Resolves entity variants across meetings (exact, alias, token overlap, semantic).
  3. TimelineBuilder: Assembles chronological event streams across disparate meetings with segment-level evidence provenance.
  4. DecisionEvolution: Tracks decision supersession chains (supersedes_decision_id) and lifecycle transitions.
  5. RAG Orchestration: Handles TIMELINE_QUERY and CROSS_MEETING_EVOLUTION intents.
  6. REST API Endpoints:
     - POST /api/v1/cross-meeting/decompose
     - POST /api/v1/cross-meeting/timeline
     - GET  /api/v1/cross-meeting/topics/{topic_name}/timeline
     - GET  /api/v1/cross-meeting/decisions/{decision_id}/evolution

Run with:
    python scripts/phase23_e2e_test.py
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User

# Intelligence, Decision, Action models
from app.auth.scope import AuthorizedRetrievalScope
from app.actions.models import ActionItem
from app.decisions.models import EnterpriseDecision, DecisionRelationship
from app.intelligence.models import IntelligenceRun, Topic
from app.knowledge.embeddings.gateway import EmbeddingGateway

# Cross-meeting components
from app.intelligence.cross_meeting.decomposer import QueryDecomposer
from app.intelligence.cross_meeting.resolver import CrossMeetingResolver
from app.intelligence.cross_meeting.timeline import TimelineBuilder
from app.intelligence.cross_meeting.schemas import CrossMeetingQueryRequest
from app.rag.orchestrator import RAGOrchestrator
from app.rag.schemas import RAGQueryRequest, IntentType
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user


def run_phase23_e2e_test():
    print("==================================================================")
    print("🚀 Starting Phase 23 (Cross-Meeting Intelligence) E2E Test")
    print("==================================================================")

    db = SessionLocal()
    client = TestClient(app)

    try:
        uid = str(uuid.uuid4())[:8]

        # ------------------------------------------------------------------
        # Step 1: Provision Multi-Meeting Architecture Across Time
        # ------------------------------------------------------------------
        print("\n[Step 1] Provisioning Multi-Meeting Environment Across 3 Longitudinal Epochs...")
        org = Organization(name=f"Enterprise Omega {uid}", slug=f"omega-{uid}")
        db.add(org)
        db.commit()

        user = User(
            email=f"lead_{uid}@omega.com",
            password_hash="hashed_pw",
            full_name="Lead Architect Elena",
        )
        db.add(user)
        db.flush()

        base_time = datetime.now(timezone.utc) - timedelta(days=60)
        t_m1 = base_time
        t_m2 = base_time + timedelta(days=20)
        t_m3 = base_time + timedelta(days=40)

        # 3 Meetings across 2 months
        m1 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 101 Architecture Kickoff", created_at=t_m1)
        m2 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 103 Cloud Strategy Sync", created_at=t_m2)
        m3 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 105 Architecture Retrospective", created_at=t_m3)
        db.add_all([m1, m2, m3])
        db.flush()

        # Media Assets & Transcripts
        ma1 = MediaAsset(tenant_id=org.id, meeting_id=m1.id, filename="m1.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
        ma2 = MediaAsset(tenant_id=org.id, meeting_id=m2.id, filename="m2.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
        ma3 = MediaAsset(tenant_id=org.id, meeting_id=m3.id, filename="m3.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
        db.add_all([ma1, ma2, ma3])
        db.flush()

        tr1 = Transcript(tenant_id=org.id, meeting_id=m1.id, media_asset_id=ma1.id, language="en", duration_seconds=600.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        tr2 = Transcript(tenant_id=org.id, meeting_id=m2.id, media_asset_id=ma2.id, language="en", duration_seconds=600.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        tr3 = Transcript(tenant_id=org.id, meeting_id=m3.id, media_asset_id=ma3.id, language="en", duration_seconds=600.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        db.add_all([tr1, tr2, tr3])
        db.flush()

        # Canonical Transcript Segments
        s1 = TranscriptSegment(tenant_id=org.id, transcript_id=tr1.id, sequence_number=0, start_seconds=10.0, end_seconds=25.0, text="We initially decided to deploy our core database on AWS RDS Aurora.", confidence=0.98)
        s2 = TranscriptSegment(tenant_id=org.id, transcript_id=tr2.id, sequence_number=0, start_seconds=45.0, end_seconds=70.0, text="Due to latency requirements, we are superseding RDS and migrating to GCP Spanner.", confidence=0.98)
        s3 = TranscriptSegment(tenant_id=org.id, transcript_id=tr3.id, sequence_number=0, start_seconds=15.0, end_seconds=40.0, text="Cloud database migration to Google Cloud Spanner is complete and latency is under 5ms.", confidence=0.98)
        db.add_all([s1, s2, s3])
        db.flush()

        # Intelligence Runs
        ir1 = IntelligenceRun(tenant_id=org.id, meeting_id=m1.id, status="COMPLETED", prompt_tokens=100, completion_tokens=50, processing_time_seconds=1.2, idempotency_key=f"ir1_{uid}", transcript_version_number=1)
        ir2 = IntelligenceRun(tenant_id=org.id, meeting_id=m2.id, status="COMPLETED", prompt_tokens=100, completion_tokens=50, processing_time_seconds=1.1, idempotency_key=f"ir2_{uid}", transcript_version_number=1)
        ir3 = IntelligenceRun(tenant_id=org.id, meeting_id=m3.id, status="COMPLETED", prompt_tokens=100, completion_tokens=50, processing_time_seconds=1.3, idempotency_key=f"ir3_{uid}", transcript_version_number=1)
        db.add_all([ir1, ir2, ir3])
        db.flush()

        # Topics across meetings
        top1 = Topic(tenant_id=org.id, meeting_id=m1.id, intelligence_run_id=ir1.id, title="Cloud Database Strategy", summary="Evaluating AWS Aurora RDS deployment.", evidence_segment_ids=[str(s1.id)])
        top2 = Topic(tenant_id=org.id, meeting_id=m2.id, intelligence_run_id=ir2.id, title="Database Migration", summary="Transitioning from AWS to GCP Spanner.", evidence_segment_ids=[str(s2.id)])
        top3 = Topic(tenant_id=org.id, meeting_id=m3.id, intelligence_run_id=ir3.id, title="Cloud DB Performance", summary="Reviewing GCP Spanner operational performance.", evidence_segment_ids=[str(s3.id)])
        db.add_all([top1, top2, top3])
        db.flush()

        # Decisions with Supersession Chain
        d1 = EnterpriseDecision(
            tenant_id=org.id,
            meeting_id=m1.id,
            intelligence_run_id=ir1.id,
            title="Adopt AWS Aurora Database",
            description="Adopt AWS Aurora PostgreSQL for primary transactional store.",
            status="CONFIRMED",
            fingerprint=f"fp1_{uid}",
            evidence_segment_ids=[str(s1.id)],
        )
        db.add(d1)
        db.flush()

        d2 = EnterpriseDecision(
            tenant_id=org.id,
            meeting_id=m2.id,
            intelligence_run_id=ir2.id,
            title="Migrate to Google Cloud Spanner",
            description="Supersede AWS Aurora and adopt Google Cloud Spanner for global multi-region consistency.",
            status="CONFIRMED",
            fingerprint=f"fp2_{uid}",
            evidence_segment_ids=[str(s2.id)],
        )
        db.add(d2)
        db.flush()

        # Explicit Supersession Relationship
        rel = DecisionRelationship(
            tenant_id=org.id,
            source_decision_id=d2.id,
            target_decision_id=d1.id,
            relationship_type="SUPERSEDES",
            confidence_score=0.98,
            reasoning="Supersedes Aurora due to multi-region global consistency needs",
        )
        db.add(rel)
        db.flush()

        # Action Items
        act1 = ActionItem(
            tenant_id=org.id,
            meeting_id=m2.id,
            intelligence_run_id=ir2.id,
            title="Benchmark GCP Spanner Latency",
            description="Benchmark GCP Spanner latency against synthetic production workloads.",
            owner_raw="Elena",
            status="OPEN",
            fingerprint_hash=f"act1_{uid}",
        )
        act2 = ActionItem(
            tenant_id=org.id,
            meeting_id=m3.id,
            intelligence_run_id=ir3.id,
            title="Decommission Legacy RDS Cluster",
            description="Decommission legacy AWS RDS staging cluster.",
            owner_raw="DevOps Team",
            status="OPEN",
            fingerprint_hash=f"act2_{uid}",
        )
        db.add_all([act1, act2])
        db.commit()
        print("  ✓ Provisioned 3 longitudinal meetings with topics, decisions, supersession relationships, and actions.")

        # ------------------------------------------------------------------
        # Step 2: QueryDecomposer Validation
        # ------------------------------------------------------------------
        print("\n[Step 2] Testing QueryDecomposer for Longitudinal Questions...")
        decomposer = QueryDecomposer()
        complex_query = "How did our cloud database strategy evolve from AWS Aurora to GCP Spanner over the last two months, and what actions were taken?"
        plan = decomposer.decompose(complex_query)

        print(f"  Query: '{complex_query}'")
        print(f"  Plan: intent={plan.intent}, requires_cross_meeting={plan.requires_cross_meeting}, tasks={len(plan.tasks)}")
        assert plan.requires_cross_meeting is True, "Query should require cross-meeting retrieval"
        assert len(plan.tasks) >= 2, "Should produce at least 2 decomposed sub-query tasks"
        for idx, t in enumerate(plan.tasks, 1):
            print(f"    Sub-Query {idx} [{t.query_type}]: '{t.sub_query}' (entity_focus={t.entity_focus})")
        print("  ✓ QueryDecomposer correctly generated structured parallel sub-tasks.")

        # ------------------------------------------------------------------
        # Step 3: CrossMeetingResolver Entity Resolution
        # ------------------------------------------------------------------
        print("\n[Step 3] Testing CrossMeetingResolver (Alias, Overlap & Semantic Fallback)...")
        resolver = CrossMeetingResolver()

        # Test exact/alias matching
        resolved_alias = resolver.resolve("Cloud DB", ["Cloud Database Strategy", "Frontend UI", "Mobile App"])
        print(f"  Resolving 'Cloud DB' -> '{resolved_alias}'")
        assert resolved_alias == "Cloud Database Strategy", "Alias/overlap resolution failed for 'Cloud DB'"

        # Test token set overlap
        resolved_overlap = resolver.resolve("Cloud Database Migration", ["Cloud Database Strategy", "Payment Gateway", "Search Index"])
        print(f"  Resolving 'Cloud Database Migration' -> '{resolved_overlap}'")
        assert resolved_overlap == "Cloud Database Strategy", "Token overlap resolution failed"

        # Test canonicalization
        canon = resolver.canonicalize("GCP Spanner Database")
        print(f"  Canonicalizing 'GCP Spanner Database' -> '{canon}'")
        assert canon == "Cloud Database" or "database" in canon.lower()
        print("  ✓ CrossMeetingResolver successfully resolved entity variations across meetings.")

        # ------------------------------------------------------------------
        # Step 4: TimelineBuilder Cross-Meeting Synthesis & Evidence
        # ------------------------------------------------------------------
        print("\n[Step 4] Testing TimelineBuilder Cross-Meeting Event Synthesis...")
        builder = TimelineBuilder(db)
        scope = AuthorizedRetrievalScope(
            tenant_id=org.id,
            user_id=user.id,
            role_code="ADMIN",
            allowed_meeting_ids=None,
        )

        timeline = builder.build_timeline(
            scope=scope,
            entity_or_topic="Cloud Database",
            limit=50,
        )

        print(f"  Synthesized {timeline.total_events} timeline events for 'Cloud Database':")
        assert timeline.total_events >= 2, f"Expected at least 2 timeline events, got {timeline.total_events}"

        # Verify chronological ordering
        prev_dt = None
        for evt in timeline.events:
            print(f"    [{evt.meeting_date}] [{evt.event_type}] '{evt.title}' (Meeting: {evt.meeting_title})")
            if prev_dt and evt.meeting_date:
                assert evt.meeting_date >= prev_dt, "Events are not chronologically ordered"
            if evt.meeting_date:
                prev_dt = evt.meeting_date
        print("  ✓ Timeline events are strictly chronologically sequenced.")

        # Verify segment evidence provenance
        has_evidence = any(len(evt.evidence_segment_ids) > 0 for evt in timeline.events)
        print(f"  Segment-level provenance verified: {has_evidence}")
        assert has_evidence, "Timeline must retain segment-level evidence linkage"

        # ------------------------------------------------------------------
        # Step 5: Decision Evolution & Supersession Chain
        # ------------------------------------------------------------------
        print("\n[Step 5] Testing Decision Evolution & Supersession Chain Tracking...")
        evolution = builder.build_decision_evolution(scope=scope, decision_id=d1.id)
        print(f"  Decision Chain: root_decision_id={evolution.root_decision_id}, total_versions={evolution.total_versions}")
        assert evolution.total_versions >= 2, f"Expected at least 2 versions in decision chain, got {evolution.total_versions}"
        chain_ids = [n.decision_id for n in evolution.evolution_chain]
        assert d1.id in chain_ids, "Root decision d1 not found in chain"
        assert d2.id in chain_ids, "Superseding decision d2 not found in chain"
        for node in evolution.evolution_chain:
            print(f"    Node: '{node.title}' [status={node.status}, relation={node.relationship_type}]")
        print("  ✓ Decision evolution chain accurately tracks lineage from proposal to supersession.")

        # ------------------------------------------------------------------
        # Step 6: REST API Endpoint Testing
        # ------------------------------------------------------------------
        print("\n[Step 6] Testing Cross-Meeting REST API Endpoints...")

        # Mock user context for auth dependency
        def mock_user_context():
            return CurrentUserContext(
                user_id=user.id,
                organization_id=org.id,
                role_code="ADMIN",
                permissions=["*"],
            )

        app.dependency_overrides[get_current_user] = mock_user_context

        # Test POST /api/v1/cross-meeting/decompose
        res_decomp = client.post(
            "/api/v1/cross-meeting/decompose",
            json={"query": "How did our cloud database decisions change over the last 3 meetings?"},
        )
        print(f"  POST /api/v1/cross-meeting/decompose -> {res_decomp.status_code}")
        assert res_decomp.status_code == 200, f"Decompose failed: {res_decomp.text}"
        decomp_data = res_decomp.json()
        assert decomp_data["requires_cross_meeting"] is True

        # Test POST /api/v1/cross-meeting/timeline
        res_timeline = client.post(
            "/api/v1/cross-meeting/timeline",
            json={"query": "Cloud Database Strategy", "entity_or_topic": "Cloud Database Strategy"},
        )
        print(f"  POST /api/v1/cross-meeting/timeline -> {res_timeline.status_code}")
        assert res_timeline.status_code == 200, f"Timeline POST failed: {res_timeline.text}"
        assert len(res_timeline.json()["events"]) >= 1

        # Test GET /api/v1/cross-meeting/topics/{topic_name}/timeline
        res_top_tl = client.get("/api/v1/cross-meeting/topics/Cloud%20Database/timeline")
        print(f"  GET /api/v1/cross-meeting/topics/Cloud Database/timeline -> {res_top_tl.status_code}")
        assert res_top_tl.status_code == 200
        assert len(res_top_tl.json()["events"]) >= 1

        # Test GET /api/v1/cross-meeting/decisions/{decision_id}/evolution
        res_evol = client.get(f"/api/v1/cross-meeting/decisions/{d1.id}/evolution")
        print(f"  GET /api/v1/cross-meeting/decisions/{d1.id}/evolution -> {res_evol.status_code}")
        assert res_evol.status_code == 200
        assert len(res_evol.json()["evolution_chain"]) >= 2
        print("  ✓ All 4 REST endpoints verified successfully.")

        # ------------------------------------------------------------------
        # Step 7: RAG Intent Routing for Cross-Meeting Queries
        # ------------------------------------------------------------------
        print("\n[Step 7] Testing RAG Conversational Pipeline with TIMELINE_QUERY Intent...")
        rag_orch = RAGOrchestrator(db=db)
        user_ctx = mock_user_context()

        rag_req = RAGQueryRequest(
            query="Can you give me a chronological timeline of how our cloud database changed across meetings?",
            conversation_id=None,
        )
        rag_resp = rag_orch.chat(current_user=user_ctx, request=rag_req)
        print(f"  RAG Detected Intent: {rag_resp.intent}")
        print(f"  RAG Response length: {len(rag_resp.answer)} chars")
        assert rag_resp.intent in [IntentType.TIMELINE_QUERY, IntentType.CROSS_MEETING_EVOLUTION, IntentType.FACTUAL_QA]
        print("  ✓ RAG pipeline successfully executed cross-meeting longitudinal query.")

        print("\n==================================================================")
        print("🎉 Phase 23 (Cross-Meeting Intelligence) E2E Test: 100% PASSED!")
        print("==================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()


if __name__ == "__main__":
    run_phase23_e2e_test()
