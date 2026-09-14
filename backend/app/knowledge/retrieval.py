"""
Phase 18 – Hybrid Retrieval Service

Combines:
  1. Vector Search (pgvector cosine similarity: <=> operator)
  2. Keyword Full-Text Search (PostgreSQL plainto_tsquery + ts_rank)
  3. Reciprocal Rank Fusion (RRF) reranking
  4. Strict Tenant Isolation (enforced prior to search evaluation)
  5. Citation Resolution (linking chunks to original TranscriptSegments)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.schemas import CitationSegmentSchema, HybridSearchResponse, SearchResultItem
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


class HybridRetrievalService:
    """
    Enterprise hybrid retrieval service ensuring tenant isolation,
    vector semantic search, lexical full-text search, and citation resolution.
    """

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.embedding_gateway = EmbeddingGateway()

    def search_vector(
        self,
        query: str,
        limit: int = 10,
        meeting_id: Optional[UUID] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Executes vector similarity search using pgvector cosine distance operator (<=>).
        Calculates cosine similarity score: 1.0 - distance.
        Enforces strict tenant_id filtering.
        """
        provider = self.embedding_gateway.get_provider()
        query_vector = provider.embed_text(query)

        # Build SQL query with vector distance
        # Note: pgvector cosine distance is 1.0 - cosine_similarity
        stmt = (
            self.db.query(
                KnowledgeChunk,
                KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance"),
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

    def search_keyword(
        self,
        query: str,
        limit: int = 10,
        meeting_id: Optional[UUID] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Executes PostgreSQL Full-Text Search using plainto_tsquery and ts_rank.
        Falls back gracefully to ILIKE if search_vector column has not yet populated.
        Enforces strict tenant_id filtering.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # Attempt PostgreSQL full-text search
        stmt = (
            self.db.query(
                KnowledgeChunk,
                func.ts_rank(
                    func.to_tsvector("english", KnowledgeChunk.content),
                    func.plainto_tsquery("english", clean_query),
                ).label("rank"),
            )
            .filter(
                KnowledgeChunk.tenant_id == self.tenant_id,
                func.to_tsvector("english", KnowledgeChunk.content).op("@@")(
                    func.plainto_tsquery("english", clean_query)
                ),
            )
        )
        if meeting_id:
            stmt = stmt.filter(KnowledgeChunk.meeting_id == meeting_id)

        stmt = stmt.order_by(text("rank DESC")).limit(limit)
        results = stmt.all()

        if not results:
            # Fallback ILIKE pattern for short or exact phrases
            tokens = [t for t in clean_query.split() if len(t) > 2]
            if tokens:
                like_conds = [KnowledgeChunk.content.ilike(f"%{t}%") for t in tokens]
                from sqlalchemy import or_
                fallback_stmt = (
                    self.db.query(KnowledgeChunk)
                    .filter(
                        KnowledgeChunk.tenant_id == self.tenant_id,
                        or_(*like_conds),
                    )
                )
                if meeting_id:
                    fallback_stmt = fallback_stmt.filter(KnowledgeChunk.meeting_id == meeting_id)
                fallback_results = fallback_stmt.limit(limit).all()
                return [(c, 0.5) for c in fallback_results]

        return [(chunk, round(float(rank), 4)) for chunk, rank in results]

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        rrf_k: int = 60,
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        meeting_id: Optional[UUID] = None,
    ) -> HybridSearchResponse:
        """
        Executes Hybrid Search with Reciprocal Rank Fusion (RRF).
        Formula: RRF_score(d) = sum( weight / (k + rank(d)) )
        Then resolves canonical transcript segment citations for each chunk.
        """
        # 1. Fetch top candidates from both channels
        vector_candidates = self.search_vector(query=query, limit=limit * 2, meeting_id=meeting_id)
        keyword_candidates = self.search_keyword(query=query, limit=limit * 2, meeting_id=meeting_id)

        # 2. Score via Reciprocal Rank Fusion
        fused_scores: Dict[UUID, float] = {}
        chunk_map: Dict[UUID, KnowledgeChunk] = {}
        vector_ranks: Dict[UUID, int] = {}
        keyword_ranks: Dict[UUID, int] = {}

        for rank, (chunk, _score) in enumerate(vector_candidates, start=1):
            chunk_map[chunk.id] = chunk
            vector_ranks[chunk.id] = rank
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (vector_weight / (rrf_k + rank))

        for rank, (chunk, _score) in enumerate(keyword_candidates, start=1):
            chunk_map[chunk.id] = chunk
            keyword_ranks[chunk.id] = rank
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (keyword_weight / (rrf_k + rank))

        # Sort by final RRF score descending
        sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)[:limit]

        # 3. Assemble response and resolve citations
        results: List[SearchResultItem] = []
        for cid in sorted_chunk_ids:
            chunk = chunk_map[cid]
            citations = self._resolve_citations(chunk.id)
            results.append(
                SearchResultItem(
                    chunk_id=chunk.id,
                    meeting_id=chunk.meeting_id,
                    content=chunk.content,
                    primary_topic=chunk.primary_topic,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                    score=round(fused_scores[cid], 5),
                    vector_rank=vector_ranks.get(cid),
                    keyword_rank=keyword_ranks.get(cid),
                    citations=citations,
                )
            )

        return HybridSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
        )

    def _resolve_citations(self, chunk_id: UUID) -> List[CitationSegmentSchema]:
        """Maps a knowledge chunk back to its source canonical transcript segments."""
        junctions = (
            self.db.query(KnowledgeChunkSegment)
            .filter(
                KnowledgeChunkSegment.chunk_id == chunk_id,
                KnowledgeChunkSegment.tenant_id == self.tenant_id,
            )
            .order_by(KnowledgeChunkSegment.sequence_in_chunk.asc())
            .all()
        )

        citations: List[CitationSegmentSchema] = []
        for j in junctions:
            seg = (
                self.db.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.id == j.segment_id,
                    TranscriptSegment.tenant_id == self.tenant_id,
                )
                .first()
            )
            if seg:
                speaker_name = (
                    (seg.speaker.display_name or seg.speaker.speaker_label)
                    if seg.speaker
                    else "Unknown"
                )
                citations.append(
                    CitationSegmentSchema(
                        segment_id=seg.id,
                        start_seconds=seg.start_seconds,
                        end_seconds=seg.end_seconds,
                        speaker_name=speaker_name,
                        text=seg.text,
                    )
                )
        return citations
