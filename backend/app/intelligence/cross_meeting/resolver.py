"""
Phase 23 – Cross-Meeting Entity Resolver

Identifies when disparate meeting references (e.g. "Mobile App", "Android app", "iOS client")
refer to the same underlying entity using deterministic token analysis and semantic embeddings.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set, Tuple
from uuid import UUID

from app.knowledge.embeddings.gateway import EmbeddingGateway


class CrossMeetingResolver:
    """
    Resolves entity references across distinct meetings into canonical representations.
    Combines rule-based synonym mapping, token-set overlap, and dense vector similarity.
    """

    KNOWN_ALIASES = {
        "mobile app": {"android app", "ios app", "mobile client", "phone app", "android client", "ios client"},
        "project apollo": {"apollo", "apollo rollout", "apollo platform", "apollo architecture"},
        "customer intelligence": {"customer intel", "client intelligence", "ci platform", "customer analytics"},
        "pgvector": {"postgres vector", "pg_vector", "pgvector extension", "vector database"},
        "data pipeline": {"data pipelines", "ingestion pipeline", "etl pipeline", "streaming pipeline"},
        "cloud database": {"cloud db", "cloud database strategy", "database migration", "cloud db performance", "database", "relational db", "rdbms"},
    }

    def __init__(self) -> None:
        self.gateway = EmbeddingGateway()

    def normalize(self, text: str) -> str:
        """Strips punctuation, expands common abbreviations, and lowercases text."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = clean.split()
        expanded = []
        for t in tokens:
            if t == "db":
                expanded.append("database")
            else:
                expanded.append(t)
        return " ".join(expanded)

    def canonicalize(self, raw_name: str) -> str:
        """Maps a raw name string to its canonical enterprise representation if matched."""
        norm = self.normalize(raw_name)
        if not norm:
            return raw_name

        # 1. Direct dictionary check
        for canonical, aliases in self.KNOWN_ALIASES.items():
            if norm == canonical or norm in aliases:
                return canonical.title()

        # 2. Substring matching in aliases (only for short entity phrases)
        if len(norm.split()) <= 4:
            for canonical, aliases in self.KNOWN_ALIASES.items():
                for alias in aliases:
                    if (alias in norm or norm in alias) and abs(len(norm) - len(alias)) <= 8:
                        return canonical.title()

        return raw_name.strip().title()

    def are_same_entity(self, name_a: str, name_b: str, threshold: float = 0.82) -> bool:
        """
        Determines if two names point to the same entity.
        Evaluates deterministic normalization first, then dense vector similarity.
        """
        norm_a = self.normalize(name_a)
        norm_b = self.normalize(name_b)

        if not norm_a or not norm_b:
            return False

        # 1. Exact normalized match
        if norm_a == norm_b:
            return True

        # 2. Check known aliases
        for canonical, aliases in self.KNOWN_ALIASES.items():
            all_forms = {canonical} | aliases
            if (norm_a in all_forms) and (norm_b in all_forms):
                return True
            for form in all_forms:
                if (norm_a in form or form in norm_a) and (norm_b in form or form in norm_b):
                    return True

        # 3. Token set containment / overlap
        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())
        if tokens_a and tokens_b:
            intersection = tokens_a & tokens_b
            if intersection:
                overlap = len(intersection) / min(len(tokens_a), len(tokens_b))
                if overlap >= 0.50:
                    return True

        # 4. Dense semantic similarity fallback
        try:
            sim = self.gateway.compute_similarity(norm_a, norm_b)
            return sim >= threshold
        except Exception:
            return False

    def resolve_best_match(
        self,
        target_name: str,
        candidates: List[str],
        threshold: float = 0.80,
    ) -> Tuple[Optional[str], float]:
        """Finds the best matching candidate name from a pool of candidates."""
        if not candidates:
            return None, 0.0

        best_match = None
        best_score = 0.0

        for cand in candidates:
            if self.are_same_entity(target_name, cand, threshold=threshold):
                score = 1.0 if self.normalize(target_name) == self.normalize(cand) else 0.88
                if score > best_score:
                    best_score = score
                    best_match = cand

        return best_match, best_score

    def resolve(
        self,
        target_name: str,
        candidates: List[str],
        threshold: float = 0.80,
    ) -> Optional[str]:
        """Convenience method returning the best matching candidate or None."""
        match, _ = self.resolve_best_match(target_name, candidates, threshold=threshold)
        return match
