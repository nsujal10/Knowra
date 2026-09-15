"""
Phase 25 – Word Error Rate (WER) & Character Error Rate (CER) Evaluator

Implements exact dynamic programming Levenshtein distance for automatic speech recognition (ASR) benchmarking.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


class WEREvaluator:
    """
    Computes Word Error Rate (WER) and Character Error Rate (CER)
    between reference (ground truth) and hypothesis (ASR transcript) texts.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """Standardizes text for fair ASR comparison (lowercasing, punctuation removal)."""
        clean = re.sub(r"[^\w\s]", "", text.lower())
        return " ".join(clean.split())

    def compute_levenshtein(self, ref_tokens: List[str], hyp_tokens: List[str]) -> Tuple[int, int, int, int]:
        """
        Calculates insertions (I), deletions (D), substitutions (S), and reference length (N).
        Returns (substitutions, deletions, insertions, total_ref_tokens).
        """
        r_len = len(ref_tokens)
        h_len = len(hyp_tokens)

        if r_len == 0:
            return 0, 0, h_len, 0

        # dp[i][j] stores (cost, S, D, I)
        dp = [[(0, 0, 0, 0) for _ in range(h_len + 1)] for _ in range(r_len + 1)]

        for i in range(1, r_len + 1):
            dp[i][0] = (i, 0, i, 0)
        for j in range(1, h_len + 1):
            dp[0][j] = (j, 0, 0, j)

        for i in range(1, r_len + 1):
            for j in range(1, h_len + 1):
                if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    sub_cost, s, d, ins = dp[i - 1][j - 1]
                    del_cost, ds, dd, dins = dp[i - 1][j]
                    ins_cost, is_, id_, iins = dp[i][j - 1]

                    best_cost = min(sub_cost + 1, del_cost + 1, ins_cost + 1)
                    if best_cost == sub_cost + 1:
                        dp[i][j] = (best_cost, s + 1, d, ins)
                    elif best_cost == del_cost + 1:
                        dp[i][j] = (best_cost, ds, dd + 1, dins)
                    else:
                        dp[i][j] = (best_cost, is_, id_, iins + 1)

        _, s, d, ins = dp[r_len][h_len]
        return s, d, ins, r_len

    def evaluate_wer(self, reference: str, hypothesis: str) -> Dict[str, float]:
        """
        Computes Word Error Rate.
        WER = (S + D + I) / N
        """
        norm_ref = self.normalize_text(reference)
        norm_hyp = self.normalize_text(hypothesis)

        ref_words = norm_ref.split()
        hyp_words = norm_hyp.split()

        if not ref_words:
            return {
                "wer": 0.0 if not hyp_words else 1.0,
                "substitutions": 0,
                "deletions": 0,
                "insertions": len(hyp_words),
                "reference_word_count": 0,
            }

        s, d, ins, n = self.compute_levenshtein(ref_words, hyp_words)
        wer = (s + d + ins) / float(n)

        return {
            "wer": round(wer, 4),
            "substitutions": s,
            "deletions": d,
            "insertions": ins,
            "reference_word_count": n,
        }

    def evaluate_cer(self, reference: str, hypothesis: str) -> Dict[str, float]:
        """
        Computes Character Error Rate.
        CER = (S + D + I) / N (at character level).
        """
        norm_ref = self.normalize_text(reference)
        norm_hyp = self.normalize_text(hypothesis)

        ref_chars = list(norm_ref)
        hyp_chars = list(norm_hyp)

        if not ref_chars:
            return {
                "cer": 0.0 if not hyp_chars else 1.0,
                "substitutions": 0,
                "deletions": 0,
                "insertions": len(hyp_chars),
                "reference_char_count": 0,
            }

        s, d, ins, n = self.compute_levenshtein(ref_chars, hyp_chars)
        cer = (s + d + ins) / float(n)

        return {
            "cer": round(cer, 4),
            "substitutions": s,
            "deletions": d,
            "insertions": ins,
            "reference_char_count": n,
        }
