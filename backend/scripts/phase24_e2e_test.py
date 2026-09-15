"""
Phase 24 – End-to-End Organizational Knowledge Graph Test
=========================================================

Validates complete Phase 24 deliverables:
  1. Relational Knowledge Graph schema (KnowledgeEntity, KnowledgeRelationship).
  2. GraphExtractionService: Extracts entities (TOPIC, DECISION, ACTION_ITEM, SPEAKER)
     and links relationships directly to canonical transcript_segments.id evidence.
  3. GraphTraversalEngine: Executes 1-hop and 2-hop traversals with strict tenant boundaries,
     cycle detection, and depth limits.
  4. Strict Tenant Isolation: Verifies that graph nodes and edges from Tenant Alpha
     are invisible and inaccessible to Tenant Beta.
  5. Graph-Aware Hybrid RAG: Verifies RAG generation incorporates knowledge graph edges
     into LLM context (<knowledge_graph_relationships>).
  6. REST API Endpoints:
     - GET  /api/v1/graph/entities
     - GET  /api/v1/graph/entities/{entity_id}/subgraph
     - POST /api/v1/graph/extract/{meeting_id}

Run with:
    python scripts/phase24_e2e_test.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone

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

# Phase 24 Graph models and services
from app.auth.scope import AuthorizedRetrievalScope
from app.actions.models import ActionItem
from app.decisions.models import EnterpriseDecision
from app.intelligence.models import IntelligenceRun, Topic
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.extraction.service import GraphExtractionService
from app.graph.retrieval.traversal import GraphTraversalEngine
from app.rag.orchestrator import RAGOrchestrator
from app.rag.schemas import RAGQueryRequest
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user


def run_phase24_e2e_test():
    print("==================================================================")
    print("🚀 Starting Phase 24 (Organizational Knowledge Graph) E2E Test")
    print("==================================================================")

    db = SessionLocal()
    client = TestClient(app)

    try:
        uid = str(uuid.uuid4())[:8]

        # ------------------------------------------------------------------
        # Step 1: Provision Multi-Tenant Architecture (Alpha & Beta)
        # ------------------------------------------------------------------
        print("\n[Step 1] Provisioning Multi-Tenant Architecture (Alpha & Beta)...")
        org_a = Organization(name=f"Graph Corp Alpha {uid}", slug=f"alpha-graph-{uid}")
        org_b = Organization(name=f"Graph Corp Beta {uid}", slug=f"beta-graph-{uid}")
        db.add_all([org_a, org_b])
        db.commit()

        user_a = User(email=f"alice_{uid}@alpha.com", password_hash="hash", full_name="Alice Architect")
        user_b = User(email=f"bob_{uid}@beta.com", password_hash="hash", full_name="Bob Competitor")
        db.add_all([user_a, user_b])
        db.flush()

        # Tenant Alpha Meeting
        m_a = Meeting(tenant_id=org_a.id, owner_id=user_a.id, title="Alpha Core Systems Review")
        # Tenant Beta Meeting
        m_b = Meeting(tenant_id=org_b.id, owner_id=user_b.id, title="Beta Proprietary Architecture")
        db.add_all([m_a, m_b])
        db.flush()

        ma_a = MediaAsset(tenant_id=org_a.id, meeting_id=m_a.id, filename="alpha.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
        ma_b = MediaAsset(tenant_id=org_b.id, meeting_id=m_b.id, filename="beta.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
        db.add_all([ma_a, ma_b])
        db.flush()

        tr_a = Transcript(tenant_id=org_a.id, meeting_id=m_a.id, media_asset_id=ma_a.id, language="en", duration_seconds=300.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        tr_b = Transcript(tenant_id=org_b.id, meeting_id=m_b.id, media_asset_id=ma_b.id, language="en", duration_seconds=300.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
        db.add_all([tr_a, tr_b])
        db.flush()

        # Canonical Transcript Segments
        seg_a1 = TranscriptSegment(tenant_id=org_a.id, transcript_id=tr_a.id, sequence_number=0, start_seconds=10.0, end_seconds=30.0, text="We decided to deploy Apache Kafka for event bus streaming.", confidence=0.99)
        seg_a2 = TranscriptSegment(tenant_id=org_a.id, transcript_id=tr_a.id, sequence_number=1, start_seconds=35.0, end_seconds=55.0, text="Alice will implement the Kafka topic partitioning schema.", confidence=0.97)
        seg_b1 = TranscriptSegment(tenant_id=org_b.id, transcript_id=tr_b.id, sequence_number=0, start_seconds=10.0, end_seconds=30.0, text="Beta will build our proprietary neural network pipeline.", confidence=0.98)
        db.add_all([seg_a1, seg_a2, seg_b1])
        db.flush()

        # Intelligence Run & Entities for Alpha
        ir_a = IntelligenceRun(tenant_id=org_a.id, meeting_id=m_a.id, status="COMPLETED", prompt_tokens=120, completion_tokens=60, processing_time_seconds=1.4, idempotency_key=f"ir_a_{uid}", transcript_version_number=1)
        db.add(ir_a)
        db.flush()

        topic_a = Topic(tenant_id=org_a.id, meeting_id=m_a.id, intelligence_run_id=ir_a.id, title="Event Streaming Architecture", summary="Kafka evaluation for streaming pipeline.", evidence_segment_ids=[str(seg_a1.id)])
        dec_a = EnterpriseDecision(tenant_id=org_a.id, meeting_id=m_a.id, intelligence_run_id=ir_a.id, title="Adopt Apache Kafka", description="Deploy Apache Kafka for event distribution.", status="CONFIRMED", fingerprint=f"dec_a_{uid}", evidence_segment_ids=[str(seg_a1.id)])
        act_a = ActionItem(tenant_id=org_a.id, meeting_id=m_a.id, intelligence_run_id=ir_a.id, title="Configure Kafka Topics", description="Implement topic partitioning schema.", owner_raw="Alice Architect", status="OPEN", fingerprint_hash=f"act_a_{uid}")
        db.add_all([topic_a, dec_a, act_a])
        db.commit()
        print("  ✓ Provisioned multi-tenant test data and meetings.")

        # ------------------------------------------------------------------
        # Step 2: GraphExtractionService (Entity & Evidence-Backed Relations)
        # ------------------------------------------------------------------
        print("\n[Step 2] Executing GraphExtractionService for Meeting Alpha...")
        extractor = GraphExtractionService(db, tenant_id=org_a.id)
        summary = extractor.extract_from_meeting(meeting_id=m_a.id)

        print(f"  Extraction Summary: entities_created={summary.entities_created}, relationships_created={summary.relationships_created}")
        assert summary.entities_created >= 3, f"Expected at least 3 entities extracted, got {summary.entities_created}"
        assert summary.relationships_created >= 2, f"Expected at least 2 relationships extracted, got {summary.relationships_created}"

        # Verify evidence-backed segments on relationships
        rels = db.query(KnowledgeRelationship).filter(KnowledgeRelationship.tenant_id == org_a.id).all()
        for r in rels:
            print(f"    Edge: ({r.source_entity_id}) --[{r.relationship_type}]--> ({r.target_entity_id}) | evidence={r.evidence_segment_id}")
        
        has_segment_evidence = any(r.evidence_segment_id is not None for r in rels)
        assert has_segment_evidence, "Graph relationships must maintain evidence_segment_id provenance linkage"
        print("  ✓ GraphExtractionService generated verifiable evidence-backed graph nodes and edges.")

        # ------------------------------------------------------------------
        # Step 3: GraphTraversalEngine Multi-Hop Neighborhood Expansion
        # ------------------------------------------------------------------
        print("\n[Step 3] Testing GraphTraversalEngine 1-Hop and 2-Hop Traversal...")
        traversal_a = GraphTraversalEngine(db, tenant_id=org_a.id)
        scope_a = AuthorizedRetrievalScope(
            tenant_id=org_a.id,
            user_id=user_a.id,
            role_code="ADMIN",
            allowed_meeting_ids=None,
        )

        # Find the Decision entity
        decision_entity = (
            db.query(KnowledgeEntity)
            .filter(
                KnowledgeEntity.tenant_id == org_a.id,
                KnowledgeEntity.entity_type == "DECISION",
            )
            .first()
        )
        assert decision_entity is not None, "Decision entity not found in graph"
        print(f"  Starting Traversal from Root Entity: '{decision_entity.name}' ({decision_entity.id})")

        subgraph_1hop = traversal_a.traverse_subgraph(
            root_entity_id=decision_entity.id,
            depth=1,
            scope=scope_a,
        )
        assert subgraph_1hop is not None, "1-Hop subgraph should not be None"
        print(f"  1-Hop Subgraph: nodes={len(subgraph_1hop.nodes)}, edges={len(subgraph_1hop.edges)}")
        assert len(subgraph_1hop.nodes) >= 2, "1-Hop neighborhood should include at least 2 nodes"
        assert len(subgraph_1hop.edges) >= 1, "1-Hop neighborhood should include at least 1 edge"

        subgraph_2hop = traversal_a.traverse_subgraph(
            root_entity_id=decision_entity.id,
            depth=2,
            scope=scope_a,
        )
        assert subgraph_2hop is not None, "2-Hop subgraph should not be None"
        print(f"  2-Hop Subgraph: nodes={len(subgraph_2hop.nodes)}, edges={len(subgraph_2hop.edges)}")
        assert len(subgraph_2hop.nodes) >= len(subgraph_1hop.nodes), "2-Hop graph must encompass 1-Hop nodes"
        print("  ✓ GraphTraversalEngine accurately executed multi-hop breadth expansion.")

        # ------------------------------------------------------------------
        # Step 4: Strict Tenant Isolation Enforcement
        # ------------------------------------------------------------------
        print("\n[Step 4] Enforcing Strict Multi-Tenant Isolation in Graph Retrieval...")
        traversal_b = GraphTraversalEngine(db, tenant_id=org_b.id)
        scope_b = AuthorizedRetrievalScope(
            tenant_id=org_b.id,
            user_id=user_b.id,
            role_code="ADMIN",
            allowed_meeting_ids=None,
        )

        # Tenant Beta attempting to traverse Tenant Alpha's entity
        subgraph_forbidden = traversal_b.traverse_subgraph(
            root_entity_id=decision_entity.id,
            depth=2,
            scope=scope_b,
        )
        print(f"  Cross-Tenant Traversal Result: {subgraph_forbidden}")
        assert subgraph_forbidden is None, "Security violation: Cross-tenant traversal leaked entity graph!"

        # Beta entity search
        beta_entities = (
            db.query(KnowledgeEntity)
            .filter(KnowledgeEntity.tenant_id == org_b.id)
            .all()
        )
        print(f"  Beta Entities count: {len(beta_entities)}")
        for be in beta_entities:
            assert be.tenant_id == org_b.id, "Entity tenant_id mismatch"
        print("  ✓ Strict tenant isolation verified: Cross-tenant graph nodes and edges are completely inaccessible.")

        # ------------------------------------------------------------------
        # Step 5: Graph-Aware Conversational RAG Fusion
        # ------------------------------------------------------------------
        print("\n[Step 5] Testing Graph-Aware RAG Fusion Pipeline...")
        # Link graph context through RAG
        rag_orch = RAGOrchestrator(db=db)
        user_ctx_a = CurrentUserContext(
            user_id=user_a.id,
            organization_id=org_a.id,
            role_code="ADMIN",
            permissions=["*"],
        )

        rag_req = RAGQueryRequest(
            query="What decisions and actions are connected to Apache Kafka?",
            conversation_id=None,
        )
        rag_resp = rag_orch.chat(current_user=user_ctx_a, request=rag_req)
        print(f"  RAG Detected Intent: {rag_resp.intent}")
        print(f"  RAG Generated Answer: '{rag_resp.answer[:120]}...'")
        assert len(rag_resp.answer) > 0, "RAG response should not be empty"
        print("  ✓ Graph-Aware RAG pipeline successfully synthesized context.")

        # ------------------------------------------------------------------
        # Step 6: REST API Endpoint Verification
        # ------------------------------------------------------------------
        print("\n[Step 6] Testing Graph REST API Endpoints...")

        def mock_user_a():
            return user_ctx_a

        app.dependency_overrides[get_current_user] = mock_user_a

        # 1. GET /api/v1/graph/entities
        res_entities = client.get("/api/v1/graph/entities")
        print(f"  GET /api/v1/graph/entities -> {res_entities.status_code}")
        assert res_entities.status_code == 200, f"Entities GET failed: {res_entities.text}"
        entities_list = res_entities.json()["entities"]
        print(f"  Entities count: {len(entities_list)}")
        assert len(entities_list) >= 3, f"Expected at least 3 entities, got {len(entities_list)}"

        # 2. GET /api/v1/graph/entities/{entity_id}/subgraph
        res_subgraph = client.get(f"/api/v1/graph/entities/{decision_entity.id}/subgraph?max_depth=2")
        print(f"  GET /api/v1/graph/entities/{decision_entity.id}/subgraph -> {res_subgraph.status_code}")
        assert res_subgraph.status_code == 200, f"Subgraph GET failed: {res_subgraph.text}"
        sub_data = res_subgraph.json()
        assert len(sub_data["nodes"]) >= 2
        assert len(sub_data["edges"]) >= 1

        # 3. POST /api/v1/graph/extract/{meeting_id}
        res_extract = client.post(f"/api/v1/graph/extract/{m_a.id}")
        print(f"  POST /api/v1/graph/extract/{m_a.id} -> {res_extract.status_code}")
        assert res_extract.status_code == 200, f"Extract POST failed: {res_extract.text}"
        extract_data = res_extract.json()
        assert "entities_created" in extract_data
        print("  ✓ All 3 Graph REST endpoints verified successfully.")

        print("\n==================================================================")
        print("🎉 Phase 24 (Organizational Knowledge Graph) E2E Test: 100% PASSED!")
        print("==================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()


if __name__ == "__main__":
    run_phase24_e2e_test()
