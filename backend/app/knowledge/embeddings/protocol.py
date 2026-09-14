"""
Phase 18 – Embedding Provider Protocol
"""

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Protocol defining the contract for enterprise embedding generation.
    Supports text queries, documents, and returns fixed-dimension vectors.
    """

    @property
    def dimensions(self) -> int:
        """The dimensionality of the output vector (e.g. 384 or 1536)."""
        ...

    def embed_text(self, text: str) -> List[float]:
        """Generate a single embedding vector for a query or passage."""
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of passages."""
        ...
