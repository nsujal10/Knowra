"""
Phase 22 – Conversational RAG Domain Package
"""

from typing import TYPE_CHECKING

from app.rag.schemas import (
    ChatMessageResponse,
    ConversationResponse,
    IntentType,
    RAGCitation,
    RAGQueryRequest,
    RAGQueryResponse,
)

if TYPE_CHECKING:
    from app.rag.orchestrator import RAGOrchestrator


def __getattr__(name: str):
    if name == "RAGOrchestrator":
        from app.rag.orchestrator import RAGOrchestrator
        return RAGOrchestrator
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "RAGOrchestrator",
    "IntentType",
    "RAGCitation",
    "RAGQueryRequest",
    "RAGQueryResponse",
    "ConversationResponse",
    "ChatMessageResponse",
]
