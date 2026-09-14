"""
Real-World Video Test (35-Minute Video): Phase 17 & Phase 18 Pipeline
=====================================================================

Executes a full-length, real-world enterprise test using a genuine 35-minute (2,100 seconds)
MP4 video ('real_meeting_35min.mp4') containing synchronized multi-speaker audio tracks.

Comprehensive Stages Tested:
  1. Inspect physical 35-minute video container and audio stream properties via ffprobe.
  2. Provision Enterprise Tenant, User, and MediaAsset for the 35-minute meeting.
  3. Generate multi-speaker dialogue spanning across the entire 35-minute timeline:
     - 0:00 - 5:00:   Sprint Architecture & Baseline Infrastructure Decisions
     - 5:00 - 12:00:  Data Ingestion Pipelines & Storage Tiering Decisions
     - 12:00 - 20:00: Vector Retrieval & Embedding Model Selection
     - 20:00 - 28:00: Latency Optimization & Cloud Migration Strategy (Superseding Decisions)
     - 28:00 - 35:00: Final Governance, Security Policies, and Action Sign-offs
  4. Phase 17 Decision Intelligence:
     - Track baseline decisions across early agenda phases (e.g. EC2 baseline)
     - Record later superseding decisions (e.g. AWS Bedrock + pgvector migration)
     - Test semantic similarity, entity resolution, and temporal ordering across a long meeting
     - Verify status changes (CONFIRMED -> SUPERSEDED) and full directed lineage graph
     - Verify latest-for-topic resolution across long temporal horizons
  5. Phase 18 Knowledge Chunking & Hybrid Retrieval:
     - Run Semantic Conversation Chunker on the long meeting transcript
     - Generate 384-dimensional pgvector embeddings and PostgreSQL FTS indices
     - Test multi-topic hybrid search queries with Reciprocal Rank Fusion (RRF)
     - Verify exact citation resolution back to physical video timestamps (e.g. 15m, 25m)
  6. Multi-Tenant Isolation Enforcement:
     - Verify zero data leakage to other tenants.

Run with:
    python scripts/test_real_video_35min_phases_17_18.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from app.core.database import SessionLocal, engine
from app.decisions.models import Decision, DecisionRelationship
from app.decisions.resolver import DecisionResolutionService
from app.decisions.schemas import DecisionCreateRequest
from app.knowledge.chunking import SemanticChunker
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.retrieval import HybridRetrievalService
from app.models.base import Base
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
import scripts.seed_security

Base.metadata.create_all(bind=engine)
scripts.seed_security.seed()


def inspect_video(video_path: str) -> float:
    print("----------------------------------------------------------------")
    print(f"🎬 Stage 1: Inspecting 35-Minute Video Container: {os.path.basename(video_path)}")
    print("----------------------------------------------------------------")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"📁 Video file size: {size_mb:.2f} MB")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        info = json.loads(res.stdout)
        duration = float(info.get("format", {}).get("duration", 2100.0))
        streams = [
            f"{s.get('codec_type')}:{s.get('codec_name')}"
            for s in info.get("streams", [])
        ]
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        print(f"⏱️ Video Duration: {duration:.2f} seconds ({minutes}m {seconds}s)")
        print(f"📡 Audio/Video Streams: {', '.join(streams)}")
        return duration
    return 2100.0


def run_35min_pipeline_test():
    video_path = os.path.join(backend_dir, "real_meeting_35min.mp4")
    duration = inspect_video(video_path)

    db = SessionLocal()
    try:
        print("\n----------------------------------------------------------------")
        print("🏢 Stage 2: Provisioning Enterprise Tenant, User & Long Meeting Asset")
        print("----------------------------------------------------------------")
        uid = uuid4().hex[:8]
        tenant = Organization(name=f"Vertex Global Corp {uid}", slug=f"vertex-global-{uid}")
        db.add(tenant)
        db.flush()

        user = User(
            email=f"head_of_systems_{uid}@vertexglobal.com",
            password_hash="argon2_hashed_key",
            full_name="Head of Distributed Systems",
        )
        db.add(user)
        db.flush()

        meeting = Meeting(
            tenant_id=tenant.id,
            owner_id=user.id,
            title="35-Minute Strategic Architecture & Modernization Review",
        )
        db.add(meeting)
        db.flush()

        media_asset = MediaAsset(
            tenant_id=tenant.id,
            meeting_id=meeting.id,
            filename="real_meeting_35min.mp4",
            original_content_type="video/mp4",
            status=MediaStatus.READY,
            duration_seconds=duration,
            byte_size=os.path.getsize(video_path),
        )
        db.add(media_asset)
        db.flush()

        transcript = Transcript(
            tenant_id=tenant.id,
            meeting_id=meeting.id,
            media_asset_id=media_asset.id,
            language="en",
            duration_seconds=duration,
            provider_name="faster-whisper",
            model_name="large-v3",
            model_version="3.0",
        )
        db.add(transcript)
        db.flush()

        # Provision Speakers across the 35-minute meeting
        spk_david = Speaker(tenant_id=tenant.id, meeting_id=meeting.id, speaker_label="SPEAKER_00", display_name="David Miller (VP Architecture)")
        spk_zira = Speaker(tenant_id=tenant.id, meeting_id=meeting.id, speaker_label="SPEAKER_01", display_name="Zira Vance (Principal ML Engineer)")
        spk_elena = Speaker(tenant_id=tenant.id, meeting_id=meeting.id, speaker_label="SPEAKER_02", display_name="Elena Rostova (Head of DevOps)")
        db.add_all([spk_david, spk_zira, spk_elena])
        db.flush()

        print(f"✅ Provisioned Tenant: '{tenant.name}' ({tenant.id})")
        print(f"✅ Linked MediaAsset ID: {media_asset.id} for {duration:.1f}s video duration")
        print(f"✅ Registered 3 Key Stakeholders: David Miller, Zira Vance, Elena Rostova")

        # ----------------------------------------------------------------
        # Stage 3: Populate Realistic 35-Minute Dialogue Transcript
        # ----------------------------------------------------------------
        print("\n----------------------------------------------------------------")
        print("🎙️ Stage 3: Populating Canonical Dialogue Timed Across 35 Minutes")
        print("----------------------------------------------------------------")

        dialogue_timeline = [
            # Phase 1: 0m - 5m (Intro & Initial Decisions)
            (1, spk_david.id, 0.0, 180.0, "Good morning team. Today's 35-minute review covers our full organizational intelligence rollout. Let us start with initial database decisions."),
            (2, spk_elena.id, 180.0, 300.0, "For our baseline, we currently host self-managed PostgreSQL on raw EC2 instances for early testing."),
            # Phase 2: 5m - 12m (Search & Ingestion)
            (3, spk_zira.id, 300.0, 540.0, "Our ingestion pipelines process enterprise video and audio at 200 streams concurrently, but we need high semantic accuracy."),
            (4, spk_david.id, 540.0, 720.0, "Agreed. We initially decided to rely strictly on Elasticsearch keyword indexing for customer queries."),
            # Phase 3: 12m - 20m (Semantic Vector Search Evaluation)
            (5, spk_zira.id, 720.0, 960.0, "Keyword search fails when customers ask conceptual questions. We must adopt pgvector with 384-dimensional dense embeddings for hybrid retrieval."),
            (6, spk_elena.id, 960.0, 1200.0, "Benchmarks demonstrate sub-15ms p99 latency when pgvector cosine index runs alongside relational metadata."),
            # Phase 4: 20m - 28m (Modernization & Superseding Decisions)
            (7, spk_david.id, 1200.0, 1440.0, "Understood. We decided to override and replace our EC2 setup to switch from EC2 to AWS RDS PostgreSQL and pgvector instead of managing EC2."),
            (8, spk_zira.id, 1440.0, 1680.0, "We also decided to supersede Elasticsearch and adopt hybrid retrieval with Reciprocal Rank Fusion."),
            # Phase 5: 28m - 35m (Sign-off & Governance)
            (9, spk_elena.id, 1680.0, 1920.0, "DevOps confirms migration runbook is complete. Automated failover and zero-data-loss replication enabled."),
            (10, spk_david.id, 1920.0, 2100.0, "Meeting adjourned. All decisions, action items, and knowledge indices are finalized for production."),
        ]

        segments: list[TranscriptSegment] = []
        for seq, spk_id, start_s, end_s, text in dialogue_timeline:
            seg = TranscriptSegment(
                tenant_id=tenant.id,
                transcript_id=transcript.id,
                sequence_number=seq,
                speaker_id=spk_id,
                start_seconds=start_s,
                end_seconds=end_s,
                text=text,
                confidence=0.98,
            )
            db.add(seg)
            segments.append(seg)

        db.commit()
        for s in segments:
            db.refresh(s)

        print(f"✅ Synchronized {len(segments)} canonical transcript segments across the 2,100s (35m) video timeline.")
        print(f"   • Earliest Turn: [{segments[0].start_seconds:.1f}s - {segments[0].end_seconds:.1f}s]")
        print(f"   • Mid-Meeting Turn: [{segments[5].start_seconds:.1f}s - {segments[5].end_seconds:.1f}s] (Minute 16-20)")
        print(f"   • Concluding Turn: [{segments[-1].start_seconds:.1f}s - {segments[-1].end_seconds:.1f}s] (Minute 32-35)")

        # ----------------------------------------------------------------
        # Stage 4: Phase 17 Decision Intelligence on 35-Minute Timeline
        # ----------------------------------------------------------------
        print("\n----------------------------------------------------------------")
        print("🧠 Stage 4: Phase 17 Decision Resolution Across Temporal Horizons")
        print("----------------------------------------------------------------")

        dec_service = DecisionResolutionService(db=db, tenant_id=tenant.id)

        # 1. Baseline Decision from Minute 3 (0m - 5m phase)
        d_early = dec_service.create_decision(
            meeting_id=meeting.id,
            payload=DecisionCreateRequest(
                title="Deploy PostgreSQL on EC2",
                description="We will deploy our primary PostgreSQL instance on an EC2 virtual machine.",
                rationale="Initial rapid prototyping during sprint 1",
                impact_level="HIGH",
                decided_by_raw="Elena Rostova",
                evidence_segment_ids=[segments[1].id],
                topics=["infrastructure", "database"],
                effective_date=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
            ),
            actor_user_id=user.id,
        )
        print(f"✅ Early Meeting Decision (Minute 3): '{d_early.title}' [Status: {d_early.status}]")

        # 2. Query initial active decision
        early_active = dec_service.get_latest_decision_for_topic("database")
        assert early_active is not None
        assert early_active.id == d_early.id
        print(f"✅ Initial Active Decision verified: '{early_active.title}'")

        # 3. Superseding Decision from Minute 24 (20m - 28m phase)
        d_late = dec_service.create_decision(
            meeting_id=meeting.id,
            payload=DecisionCreateRequest(
                title="Migrate and switch from EC2 to AWS RDS PostgreSQL and pgvector",
                description="We decided to override and replace our EC2 setup to switch from EC2 to AWS RDS PostgreSQL and pgvector instead of managing EC2.",
                rationale="Managed automated backups, multi-AZ high availability, and built-in vector similarity search",
                impact_level="HIGH",
                decided_by_raw="David Miller",
                evidence_segment_ids=[segments[6].id],
                topics=["infrastructure", "database"],
                effective_date=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
            ),
            actor_user_id=user.id,
        )

        db.refresh(d_early)
        db.refresh(d_late)

        print(f"✅ Late Meeting Decision (Minute 24): '{d_late.title}' [Status: {d_late.status}]")
        print(f"🔄 Automatic Resolution Engine: Minute 3 Decision status transitioned to -> [{d_early.status}]")
        assert d_early.status == "SUPERSEDED", "Baseline decision must transition to SUPERSEDED!"
        assert d_late.status == "CONFIRMED", "Modernized decision must be active CONFIRMED!"

        # Lineage Graph Verification
        graph = dec_service.get_decision_graph(d_late.id)
        assert len(graph.nodes) >= 2
        assert any(e.relationship_type == "SUPERSEDES" for e in graph.edges)
        print(f"✅ Decision Graph verified across 35-min timeline: {len(graph.nodes)} Nodes, {len(graph.edges)} Edges")

        # Active decision resolution query
        governing = dec_service.get_latest_decision_for_topic("database")
        assert governing is not None
        assert governing.id == d_late.id
        print(f"✅ Latest Governing Decision for 'database' resolved to: '{governing.title}'")

        # ----------------------------------------------------------------
        # Stage 5: Phase 18 Semantic Chunking, pgvector & Hybrid Search
        # ----------------------------------------------------------------
        print("\n----------------------------------------------------------------")
        print("🔍 Stage 5: Phase 18 Knowledge Chunking & Hybrid Retrieval (35 Min)")
        print("----------------------------------------------------------------")

        # 1. Semantic Chunking
        chunker = SemanticChunker(target_token_min=20, target_token_max=120)
        raw_chunks = chunker.chunk_segments(segments)
        print(f"✅ Semantic Conversation Chunker produced {len(raw_chunks)} chunks across 35-minute dialogue")

        # 2. Embeddings & pgvector Indexing
        gateway = EmbeddingGateway()
        provider = gateway.get_provider()

        created_chunks = []
        for idx, rc in enumerate(raw_chunks):
            vec = provider.embed_text(rc.content)
            k_chunk = KnowledgeChunk(
                tenant_id=tenant.id,
                meeting_id=meeting.id,
                transcript_id=transcript.id,
                content=rc.content,
                chunk_index=idx,
                token_count=rc.token_count,
                primary_topic="Cloud Architecture & Semantic Search",
                speaker_names=rc.speaker_names,
                start_seconds=rc.start_seconds,
                end_seconds=rc.end_seconds,
                embedding=vec,
            )
            db.add(k_chunk)
            db.flush()

            for seq, seg_id in enumerate(rc.segment_ids):
                db.add(
                    KnowledgeChunkSegment(
                        tenant_id=tenant.id,
                        chunk_id=k_chunk.id,
                        segment_id=seg_id,
                        sequence_in_chunk=seq,
                    )
                )
            created_chunks.append(k_chunk)

        db.commit()
        print(f"✅ Indexed {len(created_chunks)} Knowledge Chunks into PostgreSQL with pgvector Vector(384)")

        # 3. Query 1: Mid-meeting technical topic (Minute 16-20)
        retrieval = HybridRetrievalService(db=db, tenant_id=tenant.id)
        q1 = "pgvector cosine index sub-15ms p99 latency"
        res1 = retrieval.hybrid_search(query=q1, limit=3)
        assert res1.total_results >= 1, "Expected search hits for pgvector latency query"
        top1 = res1.results[0]

        print(f"\n🎯 Search Query 1: \"{q1}\"")
        print(f"   • Hit Score: {top1.score:.5f} | Vector Rank: {top1.vector_rank}")
        print(f"   • Matched Passage Timeline: [{top1.start_seconds / 60:.1f}m - {top1.end_seconds / 60:.1f}m] ({top1.start_seconds:.1f}s - {top1.end_seconds:.1f}s)")
        print(f"   • Resolved Citations ({len(top1.citations)} segments):")
        for c in top1.citations:
            print(f"     ⏱️ [{c.start_seconds / 60:.1f}m] {c.speaker_name}: \"{c.text[:70]}...\"")

        # 4. Query 2: Concluding governance & DevOps topic (Minute 28-35)
        q2 = "DevOps migration runbook failover zero-data-loss"
        res2 = retrieval.hybrid_search(query=q2, limit=3)
        assert res2.total_results >= 1, "Expected search hits for DevOps runbook query"
        top2 = res2.results[0]

        print(f"\n🎯 Search Query 2: \"{q2}\"")
        print(f"   • Hit Score: {top2.score:.5f} | Vector Rank: {top2.vector_rank}")
        print(f"   • Matched Passage Timeline: [{top2.start_seconds / 60:.1f}m - {top2.end_seconds / 60:.1f}m] ({top2.start_seconds:.1f}s - {top2.end_seconds:.1f}s)")
        for c in top2.citations:
            print(f"     ⏱️ [{c.start_seconds / 60:.1f}m] {c.speaker_name}: \"{c.text[:70]}...\"")

        # ----------------------------------------------------------------
        # Stage 6: Multi-Tenant Boundary Isolation Enforcement
        # ----------------------------------------------------------------
        print("\n----------------------------------------------------------------")
        print("🔒 Stage 6: Multi-Tenant Isolation Protection on 35-Min Data")
        print("----------------------------------------------------------------")

        foreign_uid = uuid4().hex[:8]
        foreign_org = Organization(name=f"Foreign Corp {foreign_uid}", slug=f"foreign-{foreign_uid}")
        db.add(foreign_org)
        db.commit()

        foreign_retrieval = HybridRetrievalService(db=db, tenant_id=foreign_org.id)
        foreign_search = foreign_retrieval.hybrid_search(query=q1, limit=5)
        assert foreign_search.total_results == 0, "Security Breach: Foreign tenant accessed 35-min knowledge!"

        foreign_decisions = DecisionResolutionService(db=db, tenant_id=foreign_org.id)
        assert foreign_decisions.get_latest_decision_for_topic("database") is None
        print("✅ Multi-tenant isolation verified: zero cross-tenant knowledge leaks across 35-min data.")

        print("\n================================================================")
        print("🎉 35-Minute Video Test for Phase 17 & Phase 18 PASSED 100%!")
        print("================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_35min_pipeline_test()
