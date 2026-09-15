"""
Phase 21 & 22 – RAG Orchestrator

Coordinates conversational intent detection, query rewriting, secure hybrid retrieval
with SQL push-down authorization, context compression, structured generation,
post-generation citation validation, persistent message storage, and enterprise audit logging.
"""

from __future__ import annotations

import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
import structlog

from app.auth.scope import AuthorizedRetrievalScope
from app.auth.service import AuthorizationService
from app.knowledge.retrieval.retriever import HybridRetriever
from app.knowledge.schemas import SearchResultItem
from app.models.audit_log import AuditLog
from app.rag.citation_validator import CitationValidator
from app.rag.compression import ContextCompressor
from app.rag.generator import RAGGenerator
from app.rag.intent import IntentDetector
from app.rag.models import ChatConversation, ChatMessage
from app.rag.query_rewriter import QueryRewriter
from app.rag.schemas import (
    IntentType,
    RAGCitation,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.schemas.auth import CurrentUserContext
from app.security.exceptions import ForbiddenException

logger = structlog.get_logger(__name__)


class RAGOrchestrator:
    """
    Central orchestration engine for Knowra conversational RAG chat.
    Enforces push-down authorization, citation verification, and comprehensive audit trails.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthorizationService(db=db)
        self.intent_detector = IntentDetector()
        self.query_rewriter = QueryRewriter()
        self.context_compressor = ContextCompressor()
        self.generator = RAGGenerator()

    def chat(
        self,
        current_user: CurrentUserContext,
        request: RAGQueryRequest,
    ) -> RAGQueryResponse:
        start_time = time.time()
        tenant_id = current_user.organization_id
        user_id = current_user.user_id

        # -------------------------------------------------------------------
        # 1. Authorization & Scope Resolution (Push-Down Enforcement)
        # -------------------------------------------------------------------
        try:
            scope: AuthorizedRetrievalScope = self.auth_service.resolve_scope(
                current_user=current_user,
                requested_meeting_id=request.meeting_id,
            )
        except ForbiddenException as exc:
            # Audit log RAG_ACCESS_DENIED
            self._log_audit(
                tenant_id=tenant_id,
                user_id=user_id,
                action="RAG_ACCESS_DENIED",
                resource_type="meeting",
                resource_id=str(request.meeting_id) if request.meeting_id else None,
                success=False,
                metadata={"reason": str(exc), "query": request.query},
            )
            raise

        # -------------------------------------------------------------------
        # 2. Conversation Thread Management
        # -------------------------------------------------------------------
        conversation = None
        if request.conversation_id:
            conversation = (
                self.db.query(ChatConversation)
                .filter(
                    ChatConversation.id == request.conversation_id,
                    ChatConversation.tenant_id == tenant_id,
                    ChatConversation.user_id == user_id,
                )
                .first()
            )
            if not conversation:
                raise ForbiddenException("Conversation not found or access denied.")

        if not conversation:
            # Generate descriptive thread title from first 50 chars of query
            title = request.query.strip()[:60]
            if len(request.query) > 60:
                title += "..."
            conversation = ChatConversation(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                meeting_id=request.meeting_id,
            )
            self.db.add(conversation)
            self.db.flush()

        # Load recent message history for conversational context
        recent_messages = (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.conversation_id == conversation.id,
                ChatMessage.tenant_id == tenant_id,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(6)
            .all()
        )
        recent_messages.reverse()
        history_dicts = [
            {"sender_type": m.sender_type, "content": m.content}
            for m in recent_messages
        ]

        # -------------------------------------------------------------------
        # 3. Intent Detection & Conversational Query Transformation
        # -------------------------------------------------------------------
        intent = self.intent_detector.detect(request.query, history=history_dicts)
        rewritten_query = self.query_rewriter.rewrite(
            query=request.query,
            intent=intent,
            history=history_dicts,
        )

        # -------------------------------------------------------------------
        # 4. Push-Down Hybrid Retrieval (pgvector + FTS + RRF + Rerank)
        # -------------------------------------------------------------------
        search_results: List[SearchResultItem] = []
        retrieval_ms = 0.0

        if intent != IntentType.CHITCHAT:
            retrieval_start = time.time()
            retriever = HybridRetriever(
                db=self.db,
                tenant_id=tenant_id,
                scope=scope,
            )
            search_resp = retriever.search(
                query=rewritten_query,
                limit=request.limit,
                meeting_id=request.meeting_id,
                scope=scope,
            )
            search_results = search_resp.results
            retrieval_ms = round((time.time() - retrieval_start) * 1000, 2)

        # -------------------------------------------------------------------
        # 5. Context Compression & Defensive Demarcation
        # -------------------------------------------------------------------
        hardened_context = self.context_compressor.build_hardened_context(search_results)

        # -------------------------------------------------------------------
        # 6. Response Generation (Structured JSON with Citations)
        # -------------------------------------------------------------------
        gen_output = self.generator.generate(
            query=request.query,
            intent=intent,
            hardened_context=hardened_context,
            search_results=search_results,
            history=history_dicts,
        )
        raw_answer = gen_output.get("answer", "")
        raw_citations = gen_output.get("citations", [])

        # -------------------------------------------------------------------
        # 7. Post-Generation Citation Validation Gate
        # -------------------------------------------------------------------
        validator = CitationValidator(db=self.db, tenant_id=tenant_id)
        verified_citations = validator.validate(
            raw_citations=raw_citations,
            retrieved_results=search_results,
        )

        # -------------------------------------------------------------------
        # 8. Persistence (User Message & Assistant Response)
        # -------------------------------------------------------------------
        user_msg = ChatMessage(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            sender_type="USER",
            content=request.query,
            intent=intent.value,
        )
        self.db.add(user_msg)

        retrieval_meta = {
            "retrieval_ms": retrieval_ms,
            "total_latency_ms": round((time.time() - start_time) * 1000, 2),
            "chunks_retrieved": len(search_results),
            "verified_citations_count": len(verified_citations),
            "scope_meeting_filter": [str(m) for m in (scope.allowed_meeting_ids or [])],
        }

        assistant_msg = ChatMessage(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            sender_type="ASSISTANT",
            content=raw_answer,
            intent=intent.value,
            rewritten_query=rewritten_query,
            citations_json=[c.model_dump(mode="json") for c in verified_citations],
            retrieval_metadata=retrieval_meta,
        )
        self.db.add(assistant_msg)
        self.db.flush()

        # -------------------------------------------------------------------
        # 9. Enterprise Audit Logging (RAG_SEARCH)
        # -------------------------------------------------------------------
        self._log_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="RAG_SEARCH",
            resource_type="chat_conversation",
            resource_id=str(conversation.id),
            success=True,
            metadata={
                "message_id": str(assistant_msg.id),
                "intent": intent.value,
                "rewritten_query": rewritten_query,
                "chunks_retrieved": len(search_results),
                "citations_verified": len(verified_citations),
            },
        )
        self.db.commit()

        return RAGQueryResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            answer=raw_answer,
            intent=intent.value,
            rewritten_query=rewritten_query,
            citations=verified_citations,
            retrieval_metadata=retrieval_meta,
        )

    def _log_audit(
        self,
        tenant_id: UUID,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        success: bool,
        metadata: dict,
    ) -> None:
        """Helper to create immutable enterprise audit records."""
        try:
            audit = AuditLog(
                organization_id=tenant_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                metadata_json=metadata,
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            logger.error("Failed to write audit log", action=action, error=str(e))
            self.db.rollback()
