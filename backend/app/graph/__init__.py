"""
Phase 24 – Organizational Knowledge Graph Package
"""

from typing import TYPE_CHECKING

from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.schemas import (
    EntitySchema,
    EntitySearchResponse,
    GraphExtractionResponse,
    RelationshipSchema,
    SubGraphResponse,
)

if TYPE_CHECKING:
    from app.graph.extraction.service import GraphExtractionService
    from app.graph.retrieval.traversal import GraphTraversalEngine


def __getattr__(name: str):
    if name == "GraphExtractionService":
        from app.graph.extraction.service import GraphExtractionService
        return GraphExtractionService
    elif name == "GraphTraversalEngine":
        from app.graph.retrieval.traversal import GraphTraversalEngine
        return GraphTraversalEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "KnowledgeEntity",
    "KnowledgeRelationship",
    "EntitySchema",
    "RelationshipSchema",
    "SubGraphResponse",
    "EntitySearchResponse",
    "GraphExtractionResponse",
    "GraphExtractionService",
    "GraphTraversalEngine",
]
