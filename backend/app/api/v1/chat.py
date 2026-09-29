"""
Phase 22 – Conversational RAG Chat API Endpoints

Provides authenticated enterprise chat with push-down authorization,
canonical citation resolution, session management, SSE streaming, IDOR defense, and audit trail logging.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.service import AuthorizationService
from app.core.database import get_db
from app.models.meeting import Meeting
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


class ChatQueryFlexibleRequest(BaseModel):
    query: Optional[str] = Field(None, description="Conversational user query")
    content: Optional[str] = Field(None, description="Alternative key for query")
    conversation_id: Optional[UUID] = Field(None, description="Existing conversation UUID")
    session_id: Optional[UUID] = Field(None, description="Alternative key for conversation UUID")
    meeting_id: Optional[UUID] = Field(None, description="Optional meeting filter constraint")
    limit: int = Field(5, ge=1, le=20, description="Max context chunks to retrieve")


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field("New Chat", description="Title of the conversation")
    meeting_id: Optional[UUID] = Field(None, description="Optional associated meeting ID")


def _format_citation_dict(c: Any, db: Optional[Session] = None) -> Dict[str, Any]:
    """Formats either a RAGCitation or a raw dict into frontend-compatible citation structure."""
    if hasattr(c, "model_dump"):
        data = c.model_dump(mode="json")
    elif isinstance(c, dict):
        data = dict(c)
    else:
        data = {}

    chunk_id = str(data.get("chunk_id", ""))
    segment_id = str(data.get("segment_id", ""))
    meeting_id = str(data.get("meeting_id", "")) if data.get("meeting_id") else None
    meeting_title = data.get("meeting_title")
    quote = data.get("quote", data.get("text", ""))
    speaker = data.get("speaker_name", data.get("speaker", "Speaker"))
    start_sec = float(data.get("start_seconds", data.get("timestamp", 0.0)))
    end_sec = float(data.get("end_seconds", 0.0))
    verified = bool(data.get("verified", True))

    return {
        "chunk_id": chunk_id,
        "segment_id": segment_id,
        "meeting_id": meeting_id,
        "meeting_title": meeting_title or "Meeting Transcript",
        "text": quote,
        "quote": quote,
        "speaker": speaker,
        "speaker_name": speaker,
        "timestamp": start_sec,
        "start_seconds": start_sec,
        "end_seconds": end_sec,
        "relevance_score": 0.95,
        "verified": verified,
    }


def _execute_rag(
    db: Session,
    current_user: CurrentUserContext,
    effective_query: str,
    conv_id: Optional[UUID],
    meeting_id: Optional[UUID],
    limit: int = 5,
) -> Dict[str, Any]:
    rag_req = RAGQueryRequest(
        query=effective_query,
        conversation_id=conv_id,
        meeting_id=meeting_id,
        limit=limit,
    )
    orchestrator = RAGOrchestrator(db=db)
    try:
        resp = orchestrator.chat(current_user=current_user, request=rag_req)
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    formatted_citations = [_format_citation_dict(c, db) for c in resp.citations]

    return {
        "conversation_id": resp.conversation_id,
        "session_id": resp.conversation_id,
        "message_id": resp.message_id,
        "answer": resp.answer,
        "intent": resp.intent,
        "rewritten_query": resp.rewritten_query,
        "citations": formatted_citations,
        "retrieval_metadata": resp.retrieval_metadata,
    }


# ─── Chat Query Endpoints ───────────────────────────────────────────────────────

@router.post(
    "",
    summary="Execute conversational RAG chat query",
)
def chat_query(
    request: ChatQueryFlexibleRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_query = (request.query or request.content or "").strip()
    if not effective_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query content cannot be empty",
        )
    effective_conv_id = request.conversation_id or request.session_id
    return _execute_rag(
        db=db,
        current_user=current_user,
        effective_query=effective_query,
        conv_id=effective_conv_id,
        meeting_id=request.meeting_id,
        limit=request.limit,
    )


@router.post(
    "/query",
    summary="Execute conversational RAG query (session alias)",
)
def chat_query_alias(
    request: ChatQueryFlexibleRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    return chat_query(request=request, db=db, current_user=current_user)


# ─── Session / Conversation Management ─────────────────────────────────────────

@router.get(
    "/conversations",
    summary="List active conversations for current user",
)
def list_conversations(
    meeting_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    query = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.tenant_id == current_user.organization_id,
            ChatConversation.user_id == current_user.user_id,
        )
    )
    if meeting_id and isinstance(meeting_id, UUID):
        query = query.filter(ChatConversation.meeting_id == meeting_id)

    conversations = query.order_by(ChatConversation.updated_at.desc()).all()
    result = []
    for c in conversations:
        msg_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == c.id)
            .count()
        )
        result.append({
            "id": str(c.id),
            "title": c.title,
            "meeting_id": str(c.meeting_id) if c.meeting_id else None,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
            "message_count": msg_count,
        })
    return result


@router.get(
    "/sessions",
    summary="List active sessions for current user (frontend alias)",
)
def list_sessions(
    meeting_id: Optional[UUID] = Query(None, description="Optional meeting filter"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return list_conversations(meeting_id=meeting_id, db=db, current_user=current_user)


@router.post(
    "/conversations",
    summary="Create a new conversation session",
)
def create_conversation(
    req: CreateSessionRequest = CreateSessionRequest(),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    new_conv = ChatConversation(
        tenant_id=current_user.organization_id,
        user_id=current_user.user_id,
        title=req.title or "New Chat",
        meeting_id=req.meeting_id,
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {
        "id": str(new_conv.id),
        "title": new_conv.title,
        "meeting_id": str(new_conv.meeting_id) if new_conv.meeting_id else None,
        "created_at": new_conv.created_at.isoformat(),
        "updated_at": new_conv.updated_at.isoformat(),
        "message_count": 0,
    }


@router.post(
    "/sessions",
    summary="Create a new session (frontend alias)",
)
def create_session(
    req: CreateSessionRequest = CreateSessionRequest(),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    return create_conversation(req=req, db=db, current_user=current_user)


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete a conversation session and all its messages",
)
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    conv = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.tenant_id == current_user.organization_id,
            ChatConversation.user_id == current_user.user_id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    # Delete messages
    db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete()
    db.delete(conv)
    db.commit()
    return {"status": "deleted", "id": str(conversation_id)}


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a session (frontend alias)",
)
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    return delete_conversation(conversation_id=session_id, db=db, current_user=current_user)


# ─── Messages Retrieval ─────────────────────────────────────────────────────────

@router.get(
    "/conversations/{conversation_id}/messages",
    summary="Retrieve messages for a conversation thread",
)
def get_conversation_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[Dict[str, Any]]:
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

    result = []
    for m in messages:
        citations = [_format_citation_dict(c, db) for c in (m.citations_json or [])]
        result.append({
            "id": str(m.id),
            "conversation_id": str(m.conversation_id),
            "role": m.sender_type.lower(),
            "sender_type": m.sender_type,
            "content": m.content,
            "intent": m.intent,
            "rewritten_query": m.rewritten_query,
            "citations": citations,
            "citations_json": m.citations_json,
            "retrieval_metadata": m.retrieval_metadata or {},
            "created_at": m.created_at.isoformat(),
        })
    return result


@router.get(
    "/sessions/{session_id}/messages",
    summary="Retrieve messages for a session (frontend alias)",
)
def get_session_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_conversation_messages(conversation_id=session_id, db=db, current_user=current_user)


# ─── Real-Time SSE Streaming ───────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/stream",
    summary="Stream conversational RAG response (Server-Sent Events)",
)
async def stream_chat_session(
    session_id: UUID,
    request: ChatQueryFlexibleRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    effective_query = (request.query or request.content or "").strip()
    if not effective_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query content cannot be empty",
        )

    # Execute orchestrator asynchronously in executor
    loop = asyncio.get_event_loop()
    rag_result = await loop.run_in_executor(
        None,
        _execute_rag,
        db,
        current_user,
        effective_query,
        session_id,
        request.meeting_id,
        request.limit,
    )

    full_answer = rag_result["answer"]
    citations = rag_result["citations"]

    async def event_generator():
        # Stream response tokens/words for smooth ChatGPT typing feel
        words = full_answer.split(" ")
        chunk_size = 2
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            payload = json.dumps({"delta": chunk})
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.025)

        # Send final citations event
        if citations:
            citation_payload = json.dumps({"type": "citations", "citations": citations})
            yield f"data: {citation_payload}\n\n"

        # Signal completion
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── IDOR-Protected Citation Detail Gate ────────────────────────────────────────

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

    meeting_title = "Meeting"
    if transcript and transcript.meeting_id:
        m = db.query(Meeting).filter(Meeting.id == transcript.meeting_id).first()
        if m:
            meeting_title = m.title

    return {
        "segment_id": segment.id,
        "meeting_id": transcript.meeting_id if transcript else None,
        "meeting_title": meeting_title,
        "start_seconds": segment.start_seconds,
        "end_seconds": segment.end_seconds,
        "speaker_name": speaker_name,
        "text": segment.text,
    }
