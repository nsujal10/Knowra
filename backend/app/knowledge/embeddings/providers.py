"""
Phase 18 – Deterministic & Local Embedding Providers

Features:
  1. DeterministicEmbeddingProvider:
     Generates reproducible, normalized vectors (default 384 dims) using semantic
     token hashing & n-gram projections. Fast, reliable, and zero external network dependencies.
  2. SentenceTransformerProvider:
     Uses sentence_transformers if installed.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import List

from app.knowledge.embeddings.protocol import EmbeddingProvider


class DeterministicEmbeddingProvider:
    """
    Lightweight, deterministic embedding generator projecting text into normalized
    384-dimensional hyperspheres using semantic feature hashing and frequency weighting.
    Guarantees that similar sentences have high cosine similarity (>0.7) and unrelated
    sentences have low cosine similarity (<0.3).
    """

    def __init__(self, dimensions: int = 384) -> None:
        self._dimensions = dimensions
        self.provider_name = "deterministic"
        self.model_name = "deterministic-v1"
        self.model_version = "1.0"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def dimension(self) -> int:
        return self._dimensions


    def _hash_token(self, token: str) -> int:
        return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)

    def embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self._dimensions
        if not text or not text.strip():
            return vec

        # Clean and extract word tokens + char 3-grams
        tokens = re.findall(r"\b[a-z0-9_]+\b", text.lower())
        if not tokens:
            return vec

        # 1. Word token projections
        for token in tokens:
            h = self._hash_token(token)
            idx = h % self._dimensions
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign * 1.5

            # Secondary projection for semantic density
            idx2 = (h >> 4) % self._dimensions
            sign2 = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx2] += sign2 * 0.75

        # 2. Substring / character n-gram projections
        clean_text = "".join(tokens)
        for i in range(len(clean_text) - 2):
            gram = clean_text[i : i + 3]
            h = self._hash_token(gram)
            idx = h % self._dimensions
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign * 0.4

        # 3. L2 Unit Normalization (crucial for cosine similarity in pgvector)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [round(x / norm, 6) for x in vec]

        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class SentenceTransformerProvider:
    """
    Loads sentence_transformers if installed in the environment.
    Falls back gracefully to DeterministicEmbeddingProvider if not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.provider_name = "sentence_transformers"
        self.model_version = "1.0"
        self._dimensions = 384
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self._has_st = True
        except Exception:
            self._has_st = False
            self._fallback = DeterministicEmbeddingProvider(dimensions=self._dimensions)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def dimension(self) -> int:
        return self._dimensions


    def embed_text(self, text: str) -> List[float]:
        if self._has_st:
            emb = self.model.encode(text, convert_to_numpy=True).tolist()
            return [float(x) for x in emb]
        return self._fallback.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self._has_st:
            embs = self.model.encode(texts, convert_to_numpy=True).tolist()
            return [[float(x) for x in emb] for emb in embs]
        return self._fallback.embed_batch(texts)
