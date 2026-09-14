"""
Phase 20 – Vector Search Engine (pgvector)

Executes dense cosine distance searches strictly enforcing tenant isolation at SQL level.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk


class VectorSearchEngine:
    """
    Executes semantic vector searches over pgvector columns.
    Enforces tenant boundaries in the WHERE clause BEFORE executing similarity math.
    """

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.gateway = EmbeddingGateway()

    def search(
        self,
        query: str,
        limit: int = 20,
        meeting_id: Optional[UUID] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Calculates cosine distance (<=>) on KnowledgeChunk.embedding.
        Returns tuples of (KnowledgeChunk, cosine_similarity).
        """
        query_vec = self.gateway.embed_text(query)

        stmt = (
            self.db.query(
                KnowledgeChunk,
                KnowledgeChunk.embedding.cosine_distance(query_vec).label("distance"),
            )
            .filter(
                KnowledgeChunk.tenant_id == self.tenant_id,
                KnowledgeChunk.embedding.isnot(None),
            )
        )
        if meeting_id:
            stmt = stmt.filter(KnowledgeChunk.meeting_id == meeting_id)

        stmt = stmt.order_by(text("distance ASC")).limit(limit)
        results = stmt.all()

        return [(chunk, round(1.0 - float(dist), 4)) for chunk, dist in results]
