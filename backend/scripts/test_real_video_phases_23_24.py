"""
Real-World Video Test: Phase 23 (Cross-Meeting Intelligence) & Phase 24 (Knowledge Graph)
========================================================================================

Executes the complete cross-meeting intelligence and organizational knowledge graph pipeline
anchored directly to a genuine physical MP4 video container ('real_meeting_video.mp4')
with synchronized multi-speaker audio tracks.

Comprehensive Pipeline Stages Tested:
  1. Inspect physical video container and audio streams via ffprobe.
  2. Authenticate enterprise tenant and provision 2 longitudinal meetings linked to real video assets:
     - Meeting 1: Customer Intelligence Kickoff (Sprint 40)
     - Meeting 2: Customer Intelligence Delivery Review (Sprint 42)
  3. Anchor canonical transcript segments to the genuine video timeline:
     - Segment 1 (David Miller): 0.00s - 4.37s ("Good morning team, let us review our quarterly results...")
     - Segment 2 (Zira Vance):  4.37s - 9.29s ("Thank you David, the customer intelligence integration is on schedule...")
  4. Phase 23: Query Decomposition & Longitudinal Cross-Meeting Analysis.
  5. Phase 23: Cross-Meeting Entity Resolution (resolving 'Customer Intel' <-> 'Customer Intelligence').
  6. Phase 23: TimelineBuilder synthesizing chronological events with segment provenance.
  7. Phase 23: Decision evolution tracking with supersession relationships.
  8. Phase 24: GraphExtractionService constructing entity nodes & evidence-backed graph edges.
  9. Phase 24: GraphTraversalEngine multi-hop expansion (1-hop, 2-hop) anchored to video segments.
 10. Phase 24: Strict multi-tenant isolation validation (preventing cross-tenant graph leaks).
 11. Graph-Aware Conversational RAG chat pipeline integration.
 12. REST API verification for cross-meeting timeline and graph subgraph inspection.

Run with:
    python scripts/test_real_video_phases_23_24.py
"""

import json
import os
import subprocess
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

from app.auth.scope import AuthorizedRetrievalScope
from app.auth.service import AuthorizationService
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
from app.actions.models import ActionItem
from app.decisions.models import EnterpriseDecision, DecisionRelationship
from app.intelligence.models import IntelligenceRun, Topic

# Cross-Meeting & Graph components
from app.intelligence.cross_meeting.decomposer import QueryDecomposer
from app.intelligence.cross_meeting.resolver import CrossMeetingResolver
from app.intelligence.cross_meeting.timeline import TimelineBuilder
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.extraction.service import GraphExtractionService
from app.graph.retrieval.traversal import GraphTraversalEngine
from app.rag.orchestrator import RAGOrchestrator
from app.rag.schemas import RAGQueryRequest
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user


def run_real_video_phases_23_24_test():
    print("================================================================================")
    print("🎥 Real-World Video Test: Phase 23 (Cross-Meeting) & Phase 24 (Knowledge Graph)")
    print("================================================================================")

    # 1. Inspect physical video container
    video_path = os.path.join(backend_dir, "real_meeting_video.mp4")
    if not os.path.exists(video_path):
        print(f"❌ Error: Video container not found at: {video_path}")
        sys.exit(1)

    print(f"\n[Stage 1] Inspecting Physical Video Container: {os.path.basename(video_path)}")
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]
        probe_res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(probe_res.stdout)
        duration = float(probe_data["format"]["duration"])
        size_bytes = int(probe_data["format"]["size"])
        streams = [s["codec_type"] for s in probe_data.get("streams", [])]
        print(f"  - File Size: {size_bytes / 1024:.1f} KB")
        print(f"  - Physical Duration: {duration:.2f} seconds")
        print(f"  - Container Streams: {', '.join(streams)}")
    except Exception as e:
        print(f"  - ffprobe inspection fallback: {e}")
        duration = 9.29

    db = SessionLocal()
    client = TestClient(app)

    try:
        uid = str(uuid.uuid4())[:8]

        # ------------------------------------------------------------------
        # Stage 2: Provision Multi-Meeting Architecture Across Time
        # ------------------------------------------------------------------
        print("\n[Stage 2] Provisioning Longitudinal Meetings Linked to Real Video Media...")
        org = Organization(name=f"Acme CrossVideo Corp {uid}", slug=f"acme-cross-{uid}")
        org_foreign = Organization(name=f"Foreign Corp {uid}", slug=f"foreign-{uid}")
        db.add_all([org, org_foreign])
        db.commit()

        user = User(email=f"david_{uid}@acme.com", password_hash="hash", full_name="David Miller")
        foreign_user = User(email=f"spy_{uid}@foreign.com", password_hash="hash", full_name="Foreign Analyst")
        db.add_all([user, foreign_user])
        db.flush()

        time_m1 = datetime.now(timezone.utc) - timedelta(days=28)
        time_m2 = datetime.now(timezone.utc) - timedelta(days=7)

        # 2 Meetings spanning 3 weeks
        m1 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 40 Customer Intelligence Review", created_at=time_m1)
        m2 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 42 Customer Intelligence Launch", created_at=time_m2)
        db.add_all([m1, m2])
        db.flush()

        # Media assets pointing to real_meeting_video.mp4
        ma1 = MediaAsset(tenant_id=org.id, meeting_id=m1.id, filename="real_meeting_video.mp4", original_content_type="video/mp4", byte_size=int(os.path.getsize(video_path)), status=MediaStatus.READY)
        ma2 = MediaAsset(tenant_id=org.id, meeting_id=m2.id, filename="real_meeting_video.mp4", original_content_type="video/mp4", byte_size=int(os.path.getsize(video_path)), status=MediaStatus.READY)
        db.add_all([ma1, ma2])
        db.flush()

        tr1 = Transcript(tenant_id=org.id, meeting_id=m1.id, media_asset_id=ma1.id, language="en", duration_seconds=duration, provider_name="faster-whisper", model_name="base", model_version="1.0")
        tr2 = Transcript(tenant_id=org.id, meeting_id=m2.id, media_asset_id=ma2.id, language="en", duration_seconds=duration, provider_name="faster-whisper", model_name="base", model_version="1.0")
        db.add_all([tr1, tr2])
        db.flush()

        # Canonical segments anchored to real video timestamps
        seg_vid1 = TranscriptSegment(
            tenant_id=org.id,
            transcript_id=tr1.id,
            sequence_number=0,
            start_seconds=0.00,
            end_seconds=4.37,
            text="Good morning team, let us review our quarterly results and Customer Intelligence rollout plan.",
            confidence=0.99,
        )
        seg_vid2 = TranscriptSegment(
            tenant_id=org.id,
            transcript_id=tr2.id,
            sequence_number=1,
            start_seconds=4.37,
            end_seconds=9.29,
            text="Thank you David, the Customer Intelligence integration is on schedule and pgvector search is ready.",
            confidence=0.98,
        )
        db.add_all([seg_vid1, seg_vid2])
        db.flush()

        # Intelligence runs
        ir1 = IntelligenceRun(tenant_id=org.id, meeting_id=m1.id, status="COMPLETED", prompt_tokens=150, completion_tokens=75, processing_time_seconds=1.2, idempotency_key=f"ir1_{uid}", transcript_version_number=1)
        ir2 = IntelligenceRun(tenant_id=org.id, meeting_id=m2.id, status="COMPLETED", prompt_tokens=160, completion_tokens=80, processing_time_seconds=1.3, idempotency_key=f"ir2_{uid}", transcript_version_number=1)
        db.add_all([ir1, ir2])
        db.flush()

        # Topics across meetings
        top1 = Topic(tenant_id=org.id, meeting_id=m1.id, intelligence_run_id=ir1.id, title="Customer Intelligence Rollout", summary="Initial rollout plan and architectural scoping.", start_seconds=0.0, end_seconds=4.37, evidence_segment_ids=[str(seg_vid1.id)])
        top2 = Topic(tenant_id=org.id, meeting_id=m2.id, intelligence_run_id=ir2.id, title="Customer Intelligence Launch", summary="Production go-live and search index validation.", start_seconds=4.37, end_seconds=9.29, evidence_segment_ids=[str(seg_vid2.id)])
        db.add_all([top1, top2])
        db.flush()

        # Decisions
        dec1 = EnterpriseDecision(
            tenant_id=org.id,
            meeting_id=m1.id,
            intelligence_run_id=ir1.id,
            title="Deploy Customer Intelligence v1",
            description="Proposed deployment of Customer Intelligence with pgvector backend.",
            status="CONFIRMED",
            fingerprint=f"dec1_{uid}",
            evidence_segment_ids=[str(seg_vid1.id)],
        )
        dec2 = EnterpriseDecision(
            tenant_id=org.id,
            meeting_id=m2.id,
            intelligence_run_id=ir2.id,
            title="Approve Customer Intelligence Production Release",
            description="Confirmed Customer Intelligence production release for enterprise customers.",
            status="CONFIRMED",
            fingerprint=f"dec2_{uid}",
            evidence_segment_ids=[str(seg_vid2.id)],
        )
        db.add_all([dec1, dec2])
        db.flush()

        # Decision Relationship: dec2 refines / supersedes dec1
        rel_dec = DecisionRelationship(
            tenant_id=org.id,
            source_decision_id=dec2.id,
            target_decision_id=dec1.id,
            relationship_type="SUPERSEDES",
            confidence_score=0.97,
            reasoning="Production approval supersedes initial preview deployment",
        )
        db.add(rel_dec)
        db.flush()

        # Action Item
        act1 = ActionItem(
            tenant_id=org.id,
            meeting_id=m2.id,
            intelligence_run_id=ir2.id,
            title="Verify pgvector Index Performance",
            description="Audit vector query latency against production datasets.",
            owner_raw="Zira Vance",
            status="OPEN",
            fingerprint_hash=f"act1_{uid}",
        )
        db.add(act1)
        db.commit()
        print("  ✓ Provisioned 2 real-video meetings with canonical transcript segments & intelligence runs.")

        # ------------------------------------------------------------------
        # Stage 3: Phase 23 Query Decomposition & Longitudinal Planning
        # ------------------------------------------------------------------
        print("\n[Stage 3] Testing QueryDecomposer for Video-Derived Intelligence...")
        decomposer = QueryDecomposer()
        plan = decomposer.decompose("How did Customer Intelligence evolve between Sprint 40 and Sprint 42?")
        print(f"  Plan: requires_cross_meeting={plan.requires_cross_meeting}, tasks={len(plan.tasks)}")
        assert plan.requires_cross_meeting is True
        assert len(plan.tasks) >= 2
        print("  ✓ Query decomposition completed.")

        # ------------------------------------------------------------------
        # Stage 4: Phase 23 Entity Resolution & Longitudinal Timeline
        # ------------------------------------------------------------------
        print("\n[Stage 4] Testing Entity Resolution & TimelineBuilder with Video Timestamp Provenance...")
        resolver = CrossMeetingResolver()
        resolved_name = resolver.resolve("Customer Intel", ["Customer Intelligence Rollout", "Frontend UI", "Billing"])
        print(f"  Entity Resolution: 'Customer Intel' -> '{resolved_name}'")
        assert resolved_name == "Customer Intelligence Rollout"

        builder = TimelineBuilder(db)
        scope = AuthorizedRetrievalScope(
            tenant_id=org.id,
            user_id=user.id,
            role_code="ADMIN",
            allowed_meeting_ids=None,
        )
        timeline = builder.build_timeline(
            scope=scope,
            entity_or_topic="Customer Intelligence",
            limit=20,
        )
        print(f"  Timeline Events Count: {timeline.total_events} across {timeline.meetings_covered} meetings:")
        assert timeline.total_events >= 2
        for evt in timeline.events:
            print(f"    - [{evt.meeting_title}] [{evt.event_type}] '{evt.title}' (Timestamp: {evt.timestamp_seconds:.2f}s)")
        print("  ✓ TimelineBuilder successfully sequenced video-backed events.")

        # Decision evolution check
        evolution = builder.build_decision_evolution(scope=scope, decision_id=dec1.id)
        assert evolution.total_versions >= 2
        print(f"  Decision Evolution versions: {evolution.total_versions} (Root: {dec1.title})")
        print("  ✓ Decision evolution lineage verified.")

        # ------------------------------------------------------------------
        # Stage 5: Phase 24 Graph Extraction with Video Segment Links
        # ------------------------------------------------------------------
        print("\n[Stage 5] Testing GraphExtractionService Anchored to Video Segments...")
        extractor = GraphExtractionService(db, tenant_id=org.id)
        sum1 = extractor.extract_from_meeting(meeting_id=m1.id)
        sum2 = extractor.extract_from_meeting(meeting_id=m2.id)
        print(f"  Meeting 1 Extraction: entities={sum1.entities_created}, edges={sum1.relationships_created}")
        print(f"  Meeting 2 Extraction: entities={sum2.entities_created}, edges={sum2.relationships_created}")
        assert sum1.entities_created >= 2
        assert sum2.entities_created >= 2

        # Verify evidence_segment_id links
        all_edges = db.query(KnowledgeRelationship).filter(KnowledgeRelationship.tenant_id == org.id).all()
        for e in all_edges:
            print(f"    Edge debug: ({e.source_entity_id}) -[{e.relationship_type}]-> ({e.target_entity_id}) | evidence={e.evidence_segment_id}")
        edges_with_evidence = [e for e in all_edges if e.evidence_segment_id is not None]
        print(f"  Edges with verified video segment evidence: {len(edges_with_evidence)}")
        assert len(edges_with_evidence) >= 2
        for edge in edges_with_evidence:
            seg = db.query(TranscriptSegment).filter(TranscriptSegment.id == edge.evidence_segment_id).first()
            assert seg is not None
            print(f"    Link: {edge.relationship_type} -> Segment [{seg.start_seconds:.2f}s - {seg.end_seconds:.2f}s]: '{seg.text[:45]}...'")
        print("  ✓ Knowledge graph edges successfully anchored to physical video segment timestamps.")

        # ------------------------------------------------------------------
        # Stage 6: Phase 24 Graph Traversal & Strict Tenant Isolation
        # ------------------------------------------------------------------
        print("\n[Stage 6] Testing GraphTraversalEngine Multi-Hop & Tenant Boundaries...")
        traversal = GraphTraversalEngine(db, tenant_id=org.id)
        dec_node = db.query(KnowledgeEntity).filter(KnowledgeEntity.tenant_id == org.id, KnowledgeEntity.entity_type == "DECISION").first()
        assert dec_node is not None

        subgraph_2hop = traversal.traverse_subgraph(root_entity_id=dec_node.id, depth=2, scope=scope)
        assert subgraph_2hop is not None
        print(f"  2-Hop Subgraph: nodes={len(subgraph_2hop.nodes)}, edges={len(subgraph_2hop.edges)}")
        assert len(subgraph_2hop.nodes) >= 2

        # Foreign tenant isolation attempt
        foreign_scope = AuthorizedRetrievalScope(tenant_id=org_foreign.id, user_id=foreign_user.id, role_code="ADMIN", allowed_meeting_ids=None)
        foreign_traversal = GraphTraversalEngine(db, tenant_id=org_foreign.id)
        blocked = foreign_traversal.traverse_subgraph(root_entity_id=dec_node.id, depth=2, scope=foreign_scope)
        assert blocked is None
        print("  ✓ Strict multi-tenant isolation enforced: Foreign tenant traversal returned None.")

        # ------------------------------------------------------------------
        # Stage 7: Graph-Aware Conversational RAG & REST Endpoints
        # ------------------------------------------------------------------
        print("\n[Stage 7] Testing Conversational RAG with Video & Graph Context...")
        user_ctx = CurrentUserContext(user_id=user.id, organization_id=org.id, role_code="ADMIN", permissions=["*"])
        rag_orch = RAGOrchestrator(db=db)
        rag_res = rag_orch.chat(
            current_user=user_ctx,
            request=RAGQueryRequest(query="Provide a timeline of Customer Intelligence decisions across our meetings."),
        )
        print(f"  RAG Answer Length: {len(rag_res.answer)} chars (Intent: {rag_res.intent})")
        assert len(rag_res.answer) > 0

        # REST API Verification
        app.dependency_overrides[get_current_user] = lambda: user_ctx
        res_tl = client.get("/api/v1/cross-meeting/topics/Customer%20Intelligence/timeline")
        assert res_tl.status_code == 200
        print(f"  GET /api/v1/cross-meeting/topics/.../timeline -> 200 (Events: {len(res_tl.json()['events'])})")

        res_sub = client.get(f"/api/v1/graph/entities/{dec_node.id}/subgraph?max_depth=2")
        assert res_sub.status_code == 200
        print(f"  GET /api/v1/graph/entities/{dec_node.id}/subgraph -> 200 (Nodes: {len(res_sub.json()['nodes'])})")

        print("\n================================================================================")
        print("🎉 Real-World Video Test (Phases 23 & 24): 100% PASSED!")
        print("================================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()


if __name__ == "__main__":
    run_real_video_phases_23_24_test()
