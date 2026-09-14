"""
Phase 20 – Reciprocal Rank Fusion (RRF)

Combines ranked lists from distinct retrieval channels (vector similarity & lexical BM25/FTS)
into a unified, deduplicated list of candidates using Reciprocal Rank Fusion mathematics.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, TypeVar
from uuid import UUID

T = TypeVar("T")


class ReciprocalRankFusion:
    """
    Implements RRF algorithm:
        RRF_Score(doc) = sum_{channel in channels} [ weight_{channel} / (k + rank_{channel}(doc)) ]
    where:
        - k is a smoothing constant (default: 60)
        - rank is 1-indexed
    """

    def __init__(self, k: int = 60) -> None:
        self.k = k

    def fuse(
        self,
        ranked_lists: List[Tuple[List[Tuple[UUID, float]], float]],
    ) -> List[Tuple[UUID, float, Dict[str, int]]]:
        """
        Takes a list of tuples: (list_of_candidates, channel_weight)
        where list_of_candidates is [(entity_id, score), ...] already ordered by rank.
        Returns sorted list of (entity_id, fused_score, channel_ranks_dict).
        """
        fused_scores: Dict[UUID, float] = {}
        channel_ranks: Dict[UUID, Dict[str, int]] = {}

        for channel_idx, (candidates, weight) in enumerate(ranked_lists):
            channel_name = f"channel_{channel_idx}"
            for rank, (entity_id, _orig_score) in enumerate(candidates, start=1):
                contribution = weight / (self.k + rank)
                fused_scores[entity_id] = fused_scores.get(entity_id, 0.0) + contribution

                if entity_id not in channel_ranks:
                    channel_ranks[entity_id] = {}
                channel_ranks[entity_id][channel_name] = rank

        # Sort descending by fused RRF score
        sorted_entities = sorted(
            fused_scores.keys(),
            key=lambda eid: fused_scores[eid],
            reverse=True,
        )

        return [
            (eid, round(fused_scores[eid], 6), channel_ranks[eid])
            for eid in sorted_entities
        ]
