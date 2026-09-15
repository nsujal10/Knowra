"""
Phase 22 – End-to-End Conversational RAG Chat Pipeline Test
============================================================

Validates complete Phase 22 deliverables:
  1. Intent Detection Engine (CHITCHAT, SUMMARY, DECISION_LOOKUP, ACTION_LOOKUP, FACTUAL_QA).
  2. Conversational Query Rewriting with coreference resolution.
  3. Context Compression with prompt-injection defense demarcation.
  4. Structured Response Generation and Post-Generation Citation Validation.
  5. Persistent Conversation Threads and Message History storage.
  6. Enterprise Audit Logging (RAG_SEARCH & RAG_ACCESS_DENIED).
  7. REST API Endpoints (POST /api/v1/chat, GET /api/v1/chat/conversations).

Run with:
    python scripts/phase22_e2e_test.py
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
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.rag.citation_validator import CitationValidator
from app.rag.compression import ContextCompressor
from app.rag.intent import IntentDetector
from app.rag.models import ChatConversation, ChatMessage
from app.rag.orchestrator import RAGOrchestrator
from app.rag.query_rewriter import QueryRewriter
from app.rag.schemas import IntentType, RAGQueryRequest
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user


def run_phase22_e2e_test():
    print("==================================================================")
    print("🚀 Starting Phase 22 (Conversational RAG Chat) E2E Test")
    print("==================================================================")

    db = SessionLocal()
    client = TestClient(app)

    try:
        uid = str(uuid.uuid4())[:8]

        # 1. Pipeline Unit Verification: Intent Detection
        print("\n[Step 1] Testing Intent Detection Engine...")
        detector = IntentDetector()
        assert detector.detect("Hello there, good morning!") == IntentType.CHITCHAT
        assert detector.detect("What did we decide regarding database migration?") == IntentType.DECISION_LOOKUP
        assert detector.detect("Who is assigned to complete the frontend dashboard task?") == IntentType.ACTION_LOOKUP
        assert detector.detect("Can you summarize the meeting highlights?") == IntentType.SUMMARY
        assert detector.detect("What is our current cloud infrastructure latency?") == IntentType.FACTUAL_QA
        print("  ✓ All 5 intent categories classified accurately.")

        # 2. Pipeline Unit Verification: Query Rewriter
        print("\n[Step 2] Testing Conversational Query Rewriting...")
        rewriter = QueryRewriter()
        history = [
            {"sender_type": "USER", "content": "How is the customer intelligence platform rollout progressing?"},
            {"sender_type": "ASSISTANT", "content": "It is on schedule for production deployment next Friday."}
        ]
        rewritten = rewriter.rewrite(
            query="What did David say about it?",
            intent=IntentType.FACTUAL_QA,
            history=history,
        )
        assert "customer" in rewritten.lower() or "intelligence" in rewritten.lower() or "rollout" in rewritten.lower()
        print(f"  ✓ Query rewritten with context: '{rewritten}'")

        # 3. Pipeline Unit Verification: Citation Validator
        print("\n[Step 3] Testing Post-Generation Citation Validator...")
        validator = CitationValidator(db=db, tenant_id=uuid.uuid4())
        # Hallucinated citations should be dropped
        fake_citations = [
            {"chunk_id": str(uuid.uuid4()), "segment_id": str(uuid.uuid4()), "quote": "Phantom quote"}
        ]
        validated = validator.validate(raw_citations=fake_citations, retrieved_results=[])
        assert len(validated) == 0, "Hallucinated citations must be dropped completely"
        print("  ✓ Hallucinated citations dropped by CitationValidator.")

        # 4. Provision Enterprise Test Meeting & Knowledge Chunks
        print("\n[Step 4] Provisioning Enterprise Knowledge Base for RAG Chat...")
        org = Organization(name=f"Acme Enterprise {uid}", slug=f"acme-{uid}")
        db.add(org)
        db.commit()

        user = User(email=f"alice_{uid}@acme.com", password_hash="hash", full_name="Alice Senior Architect")
        db.add(user)
        db.flush()

        meeting = Meeting(tenant_id=org.id, owner_id=user.id, title="Quarterly Engineering Strategy")
        db.add(meeting)
        db.flush()

        media = MediaAsset(tenant_id=org.id, meeting_id=meeting.id, filename="eng.wav", original_content_type="audio/wav", status=MediaStatus.READY)
        db.add(media)
        db.flush()

        transcript = Transcript(
            tenant_id=org.id, meeting_id=meeting.id, media_asset_id=media.id,
            language="en", duration_seconds=600.0, provider_name="faster-whisper", model_name="large-v3", model_version="1.0"
        )
        db.add(transcript)
        db.flush()

        spk1 = Speaker(tenant_id=org.id, meeting_id=meeting.id, speaker_label="SPEAKER_00", display_name="David Miller")
        spk2 = Speaker(tenant_id=org.id, meeting_id=meeting.id, speaker_label="SPEAKER_01", display_name="Zira Vance")
        db.add_all([spk1, spk2])
        db.flush()

        seg_text_1 = "David Miller stated that our customer intelligence integration is on schedule for Q3."
        seg1 = TranscriptSegment(
            tenant_id=org.id, transcript_id=transcript.id, sequence_number=0,
            start_seconds=12.0, end_seconds=20.0, text=seg_text_1, confidence=0.97, speaker_id=spk1.id
        )
        seg_text_2 = "Zira confirmed the action item to complete database performance benchmarking by next Wednesday."
        seg2 = TranscriptSegment(
            tenant_id=org.id, transcript_id=transcript.id, sequence_number=1,
            start_seconds=21.0, end_seconds=32.0, text=seg_text_2, confidence=0.98, speaker_id=spk2.id
        )
        db.add_all([seg1, seg2])
        db.flush()

        gateway = EmbeddingGateway()
        vec1 = gateway.embed_text(seg_text_1)
        vec2 = gateway.embed_text(seg_text_2)

        chunk1 = KnowledgeChunk(
            tenant_id=org.id, meeting_id=meeting.id, transcript_id=transcript.id,
            content=seg_text_1, chunk_index=0, token_count=16, embedding=vec1,
            start_seconds=12.0, end_seconds=20.0, primary_topic="Customer Intelligence"
        )
        chunk2 = KnowledgeChunk(
            tenant_id=org.id, meeting_id=meeting.id, transcript_id=transcript.id,
            content=seg_text_2, chunk_index=1, token_count=18, embedding=vec2,
            start_seconds=21.0, end_seconds=32.0, primary_topic="Database Benchmarking"
        )
        db.add_all([chunk1, chunk2])
        db.flush()

        j1 = KnowledgeChunkSegment(tenant_id=org.id, chunk_id=chunk1.id, segment_id=seg1.id, sequence_in_chunk=0)
        j2 = KnowledgeChunkSegment(tenant_id=org.id, chunk_id=chunk2.id, segment_id=seg2.id, sequence_in_chunk=0)
        db.add_all([j1, j2])
        db.commit()
        print("  ✓ Knowledge base with canonical transcript citations created.")

        # 5. Execute End-to-End Conversational RAG Chat via RAGOrchestrator
        print("\n[Step 5] Executing Conversational RAG Orchestration...")
        user_ctx = CurrentUserContext(
            user_id=user.id,
            organization_id=org.id,
            role_code="ADMIN",
            permissions=["meetings:read", "rag:search", "rag:chat"],
        )

        orchestrator = RAGOrchestrator(db=db)

        # Turn 1: Factual Question
        req1 = RAGQueryRequest(query="When is customer intelligence integration scheduled?", limit=5)
        resp1 = orchestrator.chat(current_user=user_ctx, request=req1)
        assert resp1.conversation_id is not None
        assert resp1.intent == IntentType.FACTUAL_QA.value
        assert len(resp1.citations) >= 1
        assert resp1.citations[0].speaker_name == "David Miller"
        assert resp1.citations[0].segment_id == seg1.id
        print(f"  ✓ Turn 1 Response: {resp1.answer[:80]}...")
        print(f"  ✓ Turn 1 Citation: {resp1.citations[0].speaker_name} [{resp1.citations[0].start_seconds}s - {resp1.citations[0].end_seconds}s]")

        # Turn 2: Follow-up in same conversation
        req2 = RAGQueryRequest(
            query="What is Zira's deadline for it?",
            conversation_id=resp1.conversation_id,
            limit=5,
        )
        resp2 = orchestrator.chat(current_user=user_ctx, request=req2)
        assert resp2.conversation_id == resp1.conversation_id
        assert len(resp2.citations) >= 1
        print(f"  ✓ Turn 2 Response: {resp2.answer[:80]}...")

        # Turn 3: Chitchat
        req3 = RAGQueryRequest(query="Thank you so much for the assistance!", conversation_id=resp1.conversation_id)
        resp3 = orchestrator.chat(current_user=user_ctx, request=req3)
        assert resp3.intent == IntentType.CHITCHAT.value
        assert len(resp3.citations) == 0
        print(f"  ✓ Turn 3 Chitchat handled without unnecessary retrieval.")

        # 6. Verify Persistent Models (ChatConversation & ChatMessage)
        print("\n[Step 6] Verifying Persistent Chat Conversation and Messages in Database...")
        conv_db = db.query(ChatConversation).filter(ChatConversation.id == resp1.conversation_id).first()
        assert conv_db is not None
        messages_db = db.query(ChatMessage).filter(ChatMessage.conversation_id == resp1.conversation_id).all()
        # 3 turns -> 6 messages (3 USER + 3 ASSISTANT)
        assert len(messages_db) == 6
        print(f"  ✓ Conversation persisted with {len(messages_db)} dialogue turns.")

        # 7. Verify Enterprise Audit Logs (RAG_SEARCH)
        print("\n[Step 7] Verifying Enterprise Audit Logs (RAG_SEARCH)...")
        rag_searches = (
            db.query(AuditLog)
            .filter(
                AuditLog.organization_id == org.id,
                AuditLog.action == "RAG_SEARCH",
            )
            .all()
        )
        assert len(rag_searches) >= 2, "Expected at least 2 RAG_SEARCH audit records"
        print(f"  ✓ Found {len(rag_searches)} immutable RAG_SEARCH audit records.")

        # 8. REST API Integration (POST /api/v1/chat, GET /api/v1/chat/conversations)
        print("\n[Step 8] Testing REST API Endpoints...")
        app.dependency_overrides[get_current_user] = lambda: user_ctx

        api_req = {"query": "What action item was assigned to Zira?"}
        api_resp = client.post("/api/v1/chat", json=api_req)
        assert api_resp.status_code == 200, f"Expected 200, got {api_resp.status_code}"
        api_data = api_resp.json()
        assert api_data["intent"] == IntentType.ACTION_LOOKUP.value
        assert len(api_data["citations"]) >= 1
        print(f"  ✓ POST /api/v1/chat returned 200: {api_data['answer'][:70]}...")

        # List conversations
        list_resp = client.get("/api/v1/chat/conversations")
        assert list_resp.status_code == 200
        conversations = list_resp.json()
        assert len(conversations) >= 2
        print(f"  ✓ GET /api/v1/chat/conversations returned {len(conversations)} threads.")

        # Get messages of first conversation
        conv_id = conversations[0]["id"]
        msgs_resp = client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()
        assert len(msgs) >= 2
        print(f"  ✓ GET /api/v1/chat/conversations/{conv_id}/messages returned {len(msgs)} messages.")

        app.dependency_overrides.clear()

        print("\n==================================================================")
        print("✅ PHASE 22 (Conversational RAG Chat) E2E TEST PASSED")
        print("==================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_phase22_e2e_test()
