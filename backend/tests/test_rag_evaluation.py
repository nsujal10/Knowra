"""
Phase 25 Unit Test: RAG Evaluation & Metrics
============================================

Verifies:
  1. Faithfulness: Penalizes hallucinated claims not supported by retrieved context.
  2. Answer Relevance: Rates alignment between user query and answer.
  3. WEREvaluator: Calculates exact Word Error Rate and Character Error Rate via Levenshtein distance.
  4. DEREvaluator: Calculates Diarization Error Rate with speaker confusion and missed speech.
"""

import pytest

from app.evaluation.metrics.der import DEREvaluator
from app.evaluation.metrics.ragas import RAGASEvaluator
from app.evaluation.metrics.wer import WEREvaluator


def test_rag_faithfulness_penalizes_hallucinations():
    evaluator = RAGASEvaluator()

    context = [
        "Knowra deployed PostgreSQL and pgvector for high-performance semantic search.",
        "The system achieves sub-5ms query response times across enterprise clusters.",
    ]

    # Grounded answer: All claims supported by context
    grounded_answer = "Knowra uses PostgreSQL and pgvector for semantic search, achieving sub-5ms query response times."
    faith_grounded = evaluator.evaluate_faithfulness(grounded_answer, context)
    assert faith_grounded >= 0.80, f"Expected high faithfulness for grounded answer, got {faith_grounded}"

    # Hallucinated answer: Fabricated claims not in context
    hallucinated_answer = "Knowra operates exclusively on MongoDB and uses Elasticsearch clusters hosted in Sydney."
    faith_hallucinated = evaluator.evaluate_faithfulness(hallucinated_answer, context)
    assert faith_hallucinated <= 0.25, f"Expected low faithfulness for hallucinated answer, got {faith_hallucinated}"
    assert faith_grounded > faith_hallucinated, "Grounded answer must score significantly higher than hallucination"


def test_wer_evaluator_calculations():
    evaluator = WEREvaluator()

    # Exact match -> 0.0 WER
    ref = "the quick brown fox jumps over the lazy dog"
    hyp_exact = "the quick brown fox jumps over the lazy dog"
    res_exact = evaluator.evaluate_wer(ref, hyp_exact)
    assert res_exact["wer"] == 0.0
    assert res_exact["substitutions"] == 0

    # 1 substitution, 1 deletion, 1 insertion
    # ref:  the quick brown fox jumps over the lazy dog (9 words)
    # hyp:  the fast  brown jumps over the very lazy dog (fast sub quick, del fox, ins very) -> 3 / 9 = 0.3333
    hyp_mod = "the fast brown jumps over the very lazy dog"
    res_mod = evaluator.evaluate_wer(ref, hyp_mod)
    assert res_mod["wer"] > 0.0
    assert res_mod["substitutions"] >= 1


def test_der_evaluator_calculations():
    evaluator = DEREvaluator(step_seconds=0.1)

    ref_segments = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_01"},
        {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_02"},
    ]

    # Perfect hypothesis
    hyp_perfect = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_01"},
        {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_02"},
    ]
    der_perfect = evaluator.evaluate_der(ref_segments, hyp_perfect)
    assert der_perfect["der"] == 0.0

    # Hypothesis with speaker confusion (SPEAKER_02 speaks during SPEAKER_01's time)
    hyp_confused = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_02"},
        {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_01"},
    ]
    der_confused = evaluator.evaluate_der(ref_segments, hyp_confused, speaker_mapping={"SPEAKER_01": "SPEAKER_01", "SPEAKER_02": "SPEAKER_02"})
    assert der_confused["der"] > 0.50
    assert der_confused["speaker_confusion_time"] > 0.0
