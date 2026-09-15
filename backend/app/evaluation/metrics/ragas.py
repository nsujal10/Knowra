"""
Phase 25 – RAG Triad & RAGAS Evaluator

Evaluates:
  1. Faithfulness: Are all factual claims in the answer grounded in the retrieved context?
  2. Answer Relevance: Does the answer address the user's specific inquiry?
  3. Context Precision: Are relevant context chunks retrieved with high ranking?
  4. Context Recall: Does the retrieved context encompass all ground-truth facts?
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.knowledge.embeddings.gateway import EmbeddingGateway


class RAGASEvaluator:
    """
    Computes RAG evaluation metrics without external dependencies.
    Uses sentence tokenization, factual claim extraction, and embedding-based semantic entailment.
    """

    def __init__(self) -> None:
        self.gateway = EmbeddingGateway()

    @staticmethod
    def extract_claims(text: str) -> List[str]:
        """Splits answer text into atomic factual sentence claims."""
        clean = text.strip()
        if not clean:
            return []
        # Split by sentence boundaries (. ! ?)
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        valid_claims = []
        for s in sentences:
            s_clean = s.strip()
            # Filter out boilerplate sentences
            if len(s_clean.split()) >= 3 and not s_clean.lower().startswith(("hello", "sure", "here is", "in summary")):
                valid_claims.append(s_clean)
        return valid_claims or [clean]

    def evaluate_faithfulness(self, answer: str, context_chunks: List[str], threshold: float = 0.65) -> float:
        """
        Measures the fraction of claims in `answer` that are grounded in `context_chunks`.
        Score ranges from 0.0 (total hallucination) to 1.0 (fully grounded).
        """
        if not answer.strip():
            return 1.0
        if not context_chunks:
            return 0.0

        claims = self.extract_claims(answer)
        if not claims:
            return 1.0

        combined_context = " ".join(context_chunks).lower()
        supported_claims = 0

        for claim in claims:
            claim_lower = claim.lower()
            claim_words = set(re.sub(r"[^\w\s]", "", claim_lower).split())
            content_words = [w for w in claim_words if len(w) > 3]

            # 1. Lexical word overlap check against context
            overlap_count = sum(1 for w in content_words if w in combined_context)
            lexical_grounded = (overlap_count / max(1, len(content_words))) >= 0.40

            # 2. Dense semantic similarity check against individual context chunks
            semantic_grounded = False
            for chunk in context_chunks:
                try:
                    sim = self.gateway.compute_similarity(claim, chunk)
                    if sim >= threshold:
                        semantic_grounded = True
                        break
                except Exception:
                    pass

            if lexical_grounded or semantic_grounded:
                supported_claims += 1

        return round(supported_claims / len(claims), 4)


    def evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """
        Measures how directly the answer addresses the question.
        Returns score in [0.0, 1.0] blending semantic similarity and keyword overlap.
        """
        if not query.strip() or not answer.strip():
            return 0.0

        dense_score = 0.0
        try:
            sim = self.gateway.compute_similarity(query, answer)
            dense_score = max(0.0, min(1.0, sim))
        except Exception:
            pass

        q_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        a_words = set(re.sub(r"[^\w\s]", "", answer.lower()).split())
        q_content = [w for w in q_words if len(w) > 3]
        lexical_score = len(set(q_content) & a_words) / max(1, len(q_content)) if q_content else 1.0

        final_score = max(dense_score, lexical_score)
        return round(min(1.0, final_score), 4)


    def evaluate_context_precision(
        self,
        query: str,
        retrieved_chunks: List[str],
        ground_truth_answer: str,
        threshold: float = 0.45,
    ) -> float:
        """
        Measures Mean Average Precision (MAP) of retrieved context chunks.
        Higher score if relevant chunks appear near the top of the ranked list.
        """
        if not retrieved_chunks:
            return 0.0

        q_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        gt_words = set(re.sub(r"[^\w\s]", "", ground_truth_answer.lower()).split())
        target_words = {w for w in (q_words | gt_words) if len(w) > 3}

        relevant_flags = []
        for chunk in retrieved_chunks:
            chunk_words = set(re.sub(r"[^\w\s]", "", chunk.lower()).split())
            lexical_rel = (len(target_words & chunk_words) / max(1, len(target_words))) >= 0.30

            dense_rel = False
            try:
                sim_gt = self.gateway.compute_similarity(chunk, ground_truth_answer)
                sim_q = self.gateway.compute_similarity(chunk, query)
                dense_rel = (sim_gt >= threshold) or (sim_q >= threshold)
            except Exception:
                pass

            is_rel = lexical_rel or dense_rel
            relevant_flags.append(1 if is_rel else 0)

        total_relevant = sum(relevant_flags)
        if total_relevant == 0:
            return 0.0

        precisions = []
        running_rel = 0
        for i, is_rel in enumerate(relevant_flags, start=1):
            if is_rel:
                running_rel += 1
                precisions.append(running_rel / i)

        score = sum(precisions) / total_relevant if precisions else 0.0
        return round(score, 4)


    def evaluate_context_recall(
        self,
        ground_truth_claims: List[str],
        retrieved_chunks: List[str],
        threshold: float = 0.65,
    ) -> float:
        """
        Measures the proportion of ground-truth claims that are represented in the retrieved context.
        """
        if not ground_truth_claims:
            return 1.0
        if not retrieved_chunks:
            return 0.0

        combined_context = " ".join(retrieved_chunks).lower()
        recalled = 0

        for claim in ground_truth_claims:
            claim_lower = claim.lower()
            claim_words = set(re.sub(r"[^\w\s]", "", claim_lower).split())
            content_words = [w for w in claim_words if len(w) > 3]
            overlap_count = sum(1 for w in content_words if w in combined_context)

            if (overlap_count / max(1, len(content_words))) >= 0.40:
                recalled += 1
            else:
                for chunk in retrieved_chunks:
                    if self.gateway.compute_similarity(claim, chunk) >= threshold:
                        recalled += 1
                        break

        return round(recalled / len(ground_truth_claims), 4)


    def evaluate_all(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculates full RAG metric suite."""
        faithfulness = self.evaluate_faithfulness(answer, retrieved_chunks)
        relevance = self.evaluate_answer_relevance(query, answer)

        gt = ground_truth or answer
        gt_claims = self.extract_claims(gt)
        precision = self.evaluate_context_precision(query, retrieved_chunks, gt)
        recall = self.evaluate_context_recall(gt_claims, retrieved_chunks)

        return {
            "faithfulness": faithfulness,
            "answer_relevance": relevance,
            "context_precision": precision,
            "context_recall": recall,
        }
