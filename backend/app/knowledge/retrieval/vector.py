"""
Phase 20 – Vector Search Engine (pgvector)

Executes dense cosine distance searches strictly enforcing tenant isolation at SQL level.
"""

from __future__ import annotations

from typing import Collection, List, Optional, Tuple
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
        allowed_meeting_ids: Optional[Collection[UUID]] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Calculates cosine distance (<=>) on KnowledgeChunk.embedding.
        Enforces tenant_id and allowed_meeting_ids push-down filters at SQL level.
        Returns tuples of (KnowledgeChunk, cosine_similarity).
        """
        # If allowed_meeting_ids is provided as empty set, user has 0 permitted meetings
        if allowed_meeting_ids is not None and len(allowed_meeting_ids) == 0:
            return []

        # If a specific meeting was requested, ensure it's permitted
        if meeting_id is not None and allowed_meeting_ids is not None and meeting_id not in allowed_meeting_ids:
            return []

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
        elif allowed_meeting_ids is not None:
            stmt = stmt.filter(KnowledgeChunk.meeting_id.in_(list(allowed_meeting_ids)))

        stmt = stmt.order_by(text("distance ASC")).limit(limit)
        results = stmt.all()

        return [(chunk, round(1.0 - float(dist), 4)) for chunk, dist in results]
