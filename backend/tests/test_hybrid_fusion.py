"""
Unit Tests: Hybrid Reciprocal Rank Fusion (Phase 20)
Verifies RRF mathematical sorting, deduplication, and score ranking between mock
keyword and vector candidate pools.
"""

import uuid
import pytest
from app.knowledge.retrieval.fusion import ReciprocalRankFusion


def test_rrf_scoring_and_deduplication():
    # Arrange: 3 candidates
    id_both = uuid.uuid4()   # Present in both vector and keyword
    id_vec_only = uuid.uuid4()
    id_kw_only = uuid.uuid4()

    vector_pool = [
        (id_both, 0.95),      # Rank 1 in vector
        (id_vec_only, 0.88),  # Rank 2 in vector
    ]

    keyword_pool = [
        (id_both, 4.5),       # Rank 1 in keyword
        (id_kw_only, 3.2),    # Rank 2 in keyword
    ]

    # Act: Fuse with k=60, equal weights 1.0
    rrf = ReciprocalRankFusion(k=60)
    fused = rrf.fuse([
        (vector_pool, 1.0),
        (keyword_pool, 1.0),
    ])

    # Assert: Exactly 3 unique candidates returned (deduplication verified)
    assert len(fused) == 3
    result_ids = [item[0] for item in fused]
    assert result_ids[0] == id_both  # Must be #1 because present in both channels at rank 1

    # Exact mathematical verification
    # rank 1 in both: 1/(60 + 1) + 1/(60 + 1) = 2 / 61 = 0.032787
    expected_top_score = round(1.0 / 61.0 + 1.0 / 61.0, 6)
    assert fused[0][1] == expected_top_score

    # Channel ranks recorded properly
    ranks_top = fused[0][2]
    assert ranks_top["channel_0"] == 1
    assert ranks_top["channel_1"] == 1

    # Rank 2 and 3 should tie at 1/62 = 0.016129
    expected_runner_up_score = round(1.0 / 62.0, 6)
    assert fused[1][1] == expected_runner_up_score
    assert fused[2][1] == expected_runner_up_score
    assert {result_ids[1], result_ids[2]} == {id_vec_only, id_kw_only}


def test_rrf_weighted_channel_preference():
    id_vec_leader = uuid.uuid4()
    id_kw_leader = uuid.uuid4()

    vector_pool = [(id_vec_leader, 0.98)]
    keyword_pool = [(id_kw_leader, 10.0)]

    # Give vector search double the weight of keyword
    rrf = ReciprocalRankFusion(k=60)
    fused = rrf.fuse([
        (vector_pool, 2.0),
        (keyword_pool, 1.0),
    ])

    assert fused[0][0] == id_vec_leader
    assert fused[1][0] == id_kw_leader
    # Vector leader score = 2.0 / 61 = 0.032787
    # Keyword leader score = 1.0 / 61 = 0.016393
    assert fused[0][1] > fused[1][1]


def test_rrf_empty_pools():
    rrf = ReciprocalRankFusion(k=60)
    fused = rrf.fuse([
        ([], 1.0),
        ([], 1.0),
    ])
    assert fused == []
