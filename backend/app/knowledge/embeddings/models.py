"""
Phase 19 – Knowledge Embedding Models (SQLAlchemy 2.0 + pgvector)

Entities:
  - KnowledgeEmbedding: Dedicated vector store entity tracking:
      - embedding vector (VECTOR(384) / configurable dimensions)
      - content_hash (SHA-256) for deterministic idempotency
      - provider_name (e.g. sentence_transformers, openai, deterministic)
      - model_name (e.g. all-MiniLM-L6-v2, text-embedding-3-small)
      - model_version
      - dimensions (384, 1536, etc.)
      - chunk_id & meeting_id foreign keys with tenant scoping
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class KnowledgeEmbedding(TenantMixin, Base):
    """
    Dedicated embedding record tracking vector state, provenance, and idempotency.
    Enforces deterministic deduplication via (tenant_id, content_hash, model_name, model_version).
    """

    __tablename__ = "knowledge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Deterministic SHA-256 hash of the normalized chunk content
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    # Provider & Model Provenance
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=384)

    # Vector embedding column (pgvector)
    # Using 384 dimensions matching all-MiniLM-L6-v2 and local embedding gateway
    embedding = mapped_column(Vector(384), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    chunk = relationship("KnowledgeChunk", backref="embeddings")
    meeting = relationship("Meeting")

    __table_args__ = (
        Index(
            "ix_knowledge_embeddings_dedup",
            "tenant_id",
            "content_hash",
            "model_name",
            "model_version",
            unique=True,
        ),
    )
