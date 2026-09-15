"""
Phase 22 – RAG Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntentType(str, Enum):
    FACTUAL_QA = "FACTUAL_QA"
    SUMMARY = "SUMMARY"
    DECISION_LOOKUP = "DECISION_LOOKUP"
    ACTION_LOOKUP = "ACTION_LOOKUP"
    CHITCHAT = "CHITCHAT"


class RAGCitation(BaseModel):
    """Verifiable citation linking generated claims back to canonical video/transcript segments."""
    chunk_id: UUID = Field(..., description="ID of the retrieved knowledge chunk")
    segment_id: UUID = Field(..., description="Canonical transcript segment ID")
    start_seconds: float = Field(0.0, description="Start timestamp in seconds")
    end_seconds: float = Field(0.0, description="End timestamp in seconds")
    speaker_name: str = Field("Unknown", description="Attributed speaker")
    quote: str = Field(..., description="Exact textual excerpt supporting the answer")
    verified: bool = Field(True, description="Whether the citation passed post-generation validation")


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User conversational query")
    conversation_id: Optional[UUID] = Field(None, description="Existing conversation UUID")
    meeting_id: Optional[UUID] = Field(None, description="Optional meeting filter constraint")
    limit: int = Field(5, ge=1, le=20, description="Max context chunks to retrieve")


class RAGQueryResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    intent: str
    rewritten_query: str
    citations: List[RAGCitation] = Field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    meeting_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender_type: str
    content: str
    intent: Optional[str] = None
    rewritten_query: Optional[str] = None
    citations_json: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
