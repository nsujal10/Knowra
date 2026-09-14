"""
Phase 20 – Hybrid Retriever Pipeline

Integrates:
  - VectorSearchEngine
  - KeywordSearchEngine
  - ReciprocalRankFusion
  - Reranker
  - Canonical Transcript Segment Citation Resolution
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.retrieval.fusion import ReciprocalRankFusion
from app.knowledge.retrieval.keyword import KeywordSearchEngine
from app.knowledge.retrieval.reranker import CrossEncoderReranker, IdentityReranker, Reranker
from app.knowledge.retrieval.vector import VectorSearchEngine
from app.knowledge.schemas import CitationSegmentSchema, HybridSearchResponse, SearchResultItem
from app.models.transcript_segment import TranscriptSegment


class HybridRetriever:
    """
    Production-grade hybrid search pipeline combining pgvector semantic search
    and PostgreSQL Full-Text Search with Reciprocal Rank Fusion and reranking.
    """

    def __init__(
        self,
        db: Session,
        tenant_id: UUID,
        reranker: Optional[Reranker] = None,
        rrf_k: int = 60,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.vector_engine = VectorSearchEngine(db=db, tenant_id=tenant_id)
        self.keyword_engine = KeywordSearchEngine(db=db, tenant_id=tenant_id)
        self.fusion_engine = ReciprocalRankFusion(k=rrf_k)
        self.reranker = reranker or CrossEncoderReranker()

    def search(
        self,
        query: str,
        limit: int = 10,
        meeting_id: Optional[UUID] = None,
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
    ) -> HybridSearchResponse:
        # 1. Retrieve candidates from both channels (over-fetch 2x for fusion)
        candidate_k = max(limit * 2, 20)
        vector_hits = self.vector_engine.search(query=query, limit=candidate_k, meeting_id=meeting_id)
        keyword_hits = self.keyword_engine.search(query=query, limit=candidate_k, meeting_id=meeting_id)

        # Build chunk map
        chunk_map = {chunk.id: chunk for chunk, _ in vector_hits}
        chunk_map.update({chunk.id: chunk for chunk, _ in keyword_hits})

        v_tuples = [(c.id, s) for c, s in vector_hits]
        k_tuples = [(c.id, s) for c, s in keyword_hits]

        # 2. Reciprocal Rank Fusion
        fused = self.fusion_engine.fuse([
            (v_tuples, vector_weight),
            (k_tuples, keyword_weight),
        ])

        # 3. Top candidates to rerank
        top_fused = fused[: candidate_k]
        candidate_chunks = [(chunk_map[eid], score) for eid, score, _ in top_fused if eid in chunk_map]

        # 4. Reranking
        reranked = self.reranker.rerank(query=query, candidates=candidate_chunks)[:limit]

        # 5. Citation Resolution
        results: List[SearchResultItem] = []
        rank_lookup = {eid: ranks for eid, _, ranks in top_fused}

        for chunk, final_score in reranked:
            citations = self.resolve_citations(chunk.id)
            ranks = rank_lookup.get(chunk.id, {})
            results.append(
                SearchResultItem(
                    chunk_id=chunk.id,
                    meeting_id=chunk.meeting_id,
                    content=chunk.content,
                    primary_topic=chunk.primary_topic,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                    score=round(final_score, 5),
                    vector_rank=ranks.get("channel_0"),
                    keyword_rank=ranks.get("channel_1"),
                    citations=citations,
                )
            )

        return HybridSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
        )

    def resolve_citations(self, chunk_id: UUID) -> List[CitationSegmentSchema]:
        """Resolves exact canonical TranscriptSegments linked to the chunk."""
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

    # Backwards compatibility aliases
    _resolve_citations = resolve_citations
    hybrid_search = search

