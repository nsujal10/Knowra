"""
Phase 22 – Conversational RAG Chat API Endpoints

Provides authenticated enterprise chat with push-down authorization,
canonical citation resolution, IDOR defense, and audit trail logging.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.service import AuthorizationService
from app.core.database import get_db
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.rag.models import ChatConversation, ChatMessage
from app.rag.orchestrator import RAGOrchestrator
from app.rag.schemas import (
    ChatMessageResponse,
    ConversationResponse,
    RAGCitation,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user
from app.security.exceptions import ForbiddenException

router = APIRouter()


@router.post(
    "",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute conversational RAG chat query",
)
def chat_query(
    request: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> RAGQueryResponse:
    """
    Executes a conversational RAG interaction:
      1. Enforces SQL push-down authorization based on user's role and accessible meetings.
      2. Performs intent classification and query rewriting.
      3. Executes secure hybrid retrieval (pgvector + FTS + RRF + CrossEncoder rerank).
      4. Compresses context behind prompt-injection defense demarcations.
      5. Generates structured answer and post-validates citations against canonical transcripts.
      6. Emits immutable RAG_SEARCH / RAG_ACCESS_DENIED audit log events.
    """
    orchestrator = RAGOrchestrator(db=db)
    try:
        return orchestrator.chat(current_user=current_user, request=request)
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    summary="List active conversations for current user",
)
def list_conversations(
    meeting_id: Optional[UUID] = Query(None, description="Optional meeting filter"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[ConversationResponse]:
    query = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.tenant_id == current_user.organization_id,
            ChatConversation.user_id == current_user.user_id,
        )
    )
    if meeting_id:
        query = query.filter(ChatConversation.meeting_id == meeting_id)

    conversations = query.order_by(ChatConversation.updated_at.desc()).all()
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[ChatMessageResponse],
    summary="Retrieve messages for a conversation thread",
)
def get_conversation_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[ChatMessageResponse]:
    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.tenant_id == current_user.organization_id,
            ChatConversation.user_id == current_user.user_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.tenant_id == current_user.organization_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.get(
    "/citations/{segment_id}",
    summary="Retrieve canonical transcript segment for a citation (IDOR Protected)",
)
def get_citation_detail(
    segment_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    """
    Direct access gate for viewing transcript citations.
    Enforces meeting-level RBAC to prevent Citation Insecure Direct Object Reference (IDOR).
    Returns HTTP 403 if the principal lacks authorization for the underlying meeting.
    """
    auth_service = AuthorizationService(db=db)
    scope = auth_service.resolve_scope(current_user=current_user)

    is_authorized = auth_service.validate_citation_access(scope=scope, segment_id=segment_id)
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to transcript citation denied (insufficient meeting privileges or cross-tenant violation).",
        )

    segment = (
        db.query(TranscriptSegment)
        .filter(
            TranscriptSegment.id == segment_id,
            TranscriptSegment.tenant_id == current_user.organization_id,
        )
        .first()
    )
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript segment not found.",
        )

    transcript = (
        db.query(Transcript)
        .filter(Transcript.id == segment.transcript_id)
        .first()
    )

    speaker_name = (
        (segment.speaker.display_name or segment.speaker.speaker_label)
        if segment.speaker
        else "Unknown"
    )

    return {
        "segment_id": segment.id,
        "meeting_id": transcript.meeting_id if transcript else None,
        "start_seconds": segment.start_seconds,
        "end_seconds": segment.end_seconds,
        "speaker_name": speaker_name,
        "text": segment.text,
    }
