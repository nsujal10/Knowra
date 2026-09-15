"""
Phase 20 – Keyword Search Engine (PostgreSQL Full-Text Search)

Executes PostgreSQL lexical search via tsvector and ts_rank with fallback.
"""

from __future__ import annotations

from typing import Collection, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.knowledge.models import KnowledgeChunk


class KeywordSearchEngine:
    """
    Executes PostgreSQL Full-Text Search using plainto_tsquery and ts_rank.
    Enforces tenant boundaries and resource authorization in the WHERE clause BEFORE executing ranking.
    """

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def search(
        self,
        query: str,
        limit: int = 20,
        meeting_id: Optional[UUID] = None,
        allowed_meeting_ids: Optional[Collection[UUID]] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        clean = query.strip()
        if not clean:
            return []

        # If allowed_meeting_ids is provided as empty set, user has 0 permitted meetings
        if allowed_meeting_ids is not None and len(allowed_meeting_ids) == 0:
            return []

        # If a specific meeting was requested, ensure it's permitted
        if meeting_id is not None and allowed_meeting_ids is not None and meeting_id not in allowed_meeting_ids:
            return []

        # 1. PostgreSQL Full-Text Search
        stmt = (
            self.db.query(
                KnowledgeChunk,
                func.ts_rank(
                    func.to_tsvector("english", KnowledgeChunk.content),
                    func.plainto_tsquery("english", clean),
                ).label("rank"),
            )
            .filter(
                KnowledgeChunk.tenant_id == self.tenant_id,
                func.to_tsvector("english", KnowledgeChunk.content).op("@@")(
                    func.plainto_tsquery("english", clean)
                ),
            )
        )
        if meeting_id:
            stmt = stmt.filter(KnowledgeChunk.meeting_id == meeting_id)
        elif allowed_meeting_ids is not None:
            stmt = stmt.filter(KnowledgeChunk.meeting_id.in_(list(allowed_meeting_ids)))

        stmt = stmt.order_by(text("rank DESC")).limit(limit)
        results = stmt.all()

        # 2. Fallback to ILIKE if no direct FTS dictionary matches
        if not results:
            tokens = [t for t in clean.split() if len(t) > 2]
            if tokens:
                like_conds = [KnowledgeChunk.content.ilike(f"%{t}%") for t in tokens]
                fallback_stmt = (
                    self.db.query(KnowledgeChunk)
                    .filter(
                        KnowledgeChunk.tenant_id == self.tenant_id,
                        or_(*like_conds),
                    )
                )
                if meeting_id:
                    fallback_stmt = fallback_stmt.filter(KnowledgeChunk.meeting_id == meeting_id)
                elif allowed_meeting_ids is not None:
                    fallback_stmt = fallback_stmt.filter(KnowledgeChunk.meeting_id.in_(list(allowed_meeting_ids)))

                fallback_results = fallback_stmt.limit(limit).all()
                return [(c, 0.5) for c in fallback_results]

        return [(chunk, round(float(rank), 4)) for chunk, rank in results]
