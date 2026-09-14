"""
Phase 18 – Embedding Gateway

Factory and interface providing configured embedding instances based on settings.
"""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.knowledge.embeddings.protocol import EmbeddingProvider
from app.knowledge.embeddings.providers import (
    DeterministicEmbeddingProvider,
    SentenceTransformerProvider,
)

logger = structlog.get_logger(__name__)


class EmbeddingGateway:
    """
    Singleton gateway for generating embeddings across Knowra.
    Supports provider configuration through EMBEDDING_PROVIDER in settings / .env.
    """

    _instance: EmbeddingProvider | None = None

    @classmethod
    def get_provider(cls) -> EmbeddingProvider:
        if cls._instance is not None:
            return cls._instance

        provider_type = getattr(settings, "EMBEDDING_PROVIDER", "deterministic").lower()

        if provider_type in {"sentence_transformers", "sentence_transformer"}:
            logger.info("Initializing SentenceTransformer embedding provider")
            cls._instance = SentenceTransformerProvider(
                model_name=getattr(settings, "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
            )
        else:
            logger.info("Initializing Deterministic embedding provider", dimensions=384)
            cls._instance = DeterministicEmbeddingProvider(dimensions=384)

        return cls._instance
