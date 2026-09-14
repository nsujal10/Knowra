"""
Phase 20 – Reranker Protocol & Implementations

Routes top fused candidates through cross-attention or score-based reranking.
"""

from __future__ import annotations

from typing import List, Protocol, Tuple, runtime_checkable
from uuid import UUID

from app.knowledge.models import KnowledgeChunk


@runtime_checkable
class Reranker(Protocol):
    """Protocol for post-fusion candidate reranking."""

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[KnowledgeChunk, float]],
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """Reranks candidates and updates final relevance scores."""
        ...


class IdentityReranker:
    """Pass-through reranker preserving fused RRF score ordering."""

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[KnowledgeChunk, float]],
    ) -> List[Tuple[KnowledgeChunk, float]]:
        return candidates


class CrossEncoderReranker:
    """
    Reranker using cross-encoder if installed, falling back gracefully to
    keyword-density boost.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(model_name)
        except Exception:
            self._model = None

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[KnowledgeChunk, float]],
    ) -> List[Tuple[KnowledgeChunk, float]]:
        if not candidates:
            return []

        if self._model is not None:
            pairs = [[query, chunk.content] for chunk, _score in candidates]
            scores = self._model.predict(pairs)
            reranked = [
                (chunk, float(score))
                for (chunk, _), score in zip(candidates, scores)
            ]
            return sorted(reranked, key=lambda x: x[1], reverse=True)

        # Fallback: Boost scores of chunks containing exact query keywords
        q_tokens = {w.lower() for w in query.split() if len(w) > 2}
        boosted = []
        for chunk, score in candidates:
            c_text = chunk.content.lower()
            matches = sum(1 for w in q_tokens if w in c_text)
            boost = 1.0 + (0.15 * matches)
            boosted.append((chunk, round(score * boost, 5)))

        return sorted(boosted, key=lambda x: x[1], reverse=True)
