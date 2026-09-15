"""
Phase 24 – Organizational Knowledge Graph Models (SQLAlchemy 2.0)

Entities:
  - KnowledgeEntity: Enterprise nodes (Persons, Projects, Topics, Decisions, Technologies).
  - KnowledgeRelationship: Evidence-backed graph edges connecting entities with transcript segment provenance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class KnowledgeEntity(TenantMixin, Base):
    """
    Node in the organizational knowledge graph.
    Represents enterprise entities (people, projects, topics, systems) across all meetings.
    """

    __tablename__ = "knowledge_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    canonical_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="TOPIC",  # PERSON | PROJECT | TOPIC | TECHNOLOGY | DECISION | ACTION
    )
    aliases: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

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
    outgoing_edges: Mapped[List[KnowledgeRelationship]] = relationship(
        "KnowledgeRelationship",
        foreign_keys="KnowledgeRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[List[KnowledgeRelationship]] = relationship(
        "KnowledgeRelationship",
        foreign_keys="KnowledgeRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )


class KnowledgeRelationship(TenantMixin, Base):
    """
    Evidence-backed directed edge in the organizational knowledge graph.
    Every relationship links strictly back to a meeting and canonical transcript segment.
    """

    __tablename__ = "knowledge_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        # OWNS | SUPERSEDES | RELATED_TO | AFFECTS | DECIDED_IN | PARTICIPATED_IN | BLOCKED_BY
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    # Evidence & Meeting Anchors (Evidence-Backed Provenance)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evidence_segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcript_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    source_entity: Mapped[KnowledgeEntity] = relationship(
        "KnowledgeEntity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_edges",
    )
    target_entity: Mapped[KnowledgeEntity] = relationship(
        "KnowledgeEntity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_edges",
    )
    meeting = relationship("Meeting")
    evidence_segment = relationship("TranscriptSegment")
