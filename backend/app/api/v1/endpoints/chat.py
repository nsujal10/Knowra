"""
Meeting-Scoped Interactive RAG Chat API Endpoint
POST /api/v1/meetings/{meeting_id}/chat
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService
from app.security.jwt import decode_access_token

router = APIRouter()
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/token", auto_error=False)


def get_optional_tenant_id(token: Optional[str] = Depends(oauth2_optional)) -> Optional[UUID]:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        org_str = payload.get("org")
        return UUID(org_str) if org_str else None
    except Exception:
        return None


@router.post(
    "/{meeting_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask Knowra AI meeting-scoped RAG assistant",
)
def meeting_rag_chat(
    meeting_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    tenant_id: Optional[UUID] = Depends(get_optional_tenant_id),
) -> ChatResponse:
    """
    Executes grounded conversational RAG query scoped to a single meeting.
    Fetches transcript segments, discussion chapters, action items,
    injects strict guardrails, and extracts interactive timestamp citation pills.
    """
    rag_service = RAGService(db=db, tenant_id=tenant_id)
    return rag_service.ask(
        meeting_id_str=meeting_id,
        query=request.message,
        history=request.history,
    )
