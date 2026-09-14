"""
Phase 18 – Knowledge Chunking & Vector Models (SQLAlchemy 2.0 + pgvector)

Entities:
  - KnowledgeChunk: Semantic passage derived from conversations with embeddings and full-text vectors
  - KnowledgeChunkSegment: Junction table linking chunks to exact TranscriptSegments for citation resolution
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
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class KnowledgeChunk(TenantMixin, Base):
    """
    Semantic knowledge chunk formed around topic boundaries and dialogue exchanges.
    Features:
      - Vector(384) embedding column for pgvector semantic search
      - TSVECTOR column for PostgreSQL Full-Text Search
      - Temporal bounds (start_seconds, end_seconds) for meeting timeline playback
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content & Semantic Metadata
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    topic_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    speaker_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Timeline bounds (seconds)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Embeddings (pgvector) & FTS (PostgreSQL TSVECTOR)
    # Using 384 dimensions for all-MiniLM-L6-v2 / local embeddings
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384), nullable=True)
    search_vector = mapped_column(TSVECTOR, nullable=True)

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
    meeting = relationship("Meeting")
    transcript = relationship("Transcript")
    chunk_segments = relationship(
        "KnowledgeChunkSegment",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )


class KnowledgeChunkSegment(TenantMixin, Base):
    """
    Junction mapping between KnowledgeChunk and canonical TranscriptSegments.
    Guarantees citation resolution back to the exact video/audio segment timestamps.
    """

    __tablename__ = "knowledge_chunk_segments"

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
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcript_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_in_chunk: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    chunk = relationship("KnowledgeChunk", back_populates="chunk_segments")
    segment = relationship("TranscriptSegment")
