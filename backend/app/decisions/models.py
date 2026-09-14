"""
Phase 17 – Decision Intelligence Models (SQLAlchemy 2.0)

Entities:
  - Decision: Enterprise decision record with lifecycle status, impact, and fingerprinting
  - DecisionEvidence: Direct provenance mapping to canonical TranscriptSegments
  - DecisionTopic: Topic/entity tags associated with decisions
  - DecisionRelationship: Graph edges capturing relationships (SUPERSEDES, REVERSES, REFINES, RELATED)
  - DecisionEvent: Immutable audit event trail for decision modifications and status changes
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

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


class EnterpriseDecision(TenantMixin, Base):
    """
    Enterprise decision entity.
    Tracks state transitions (PROPOSED, CONFIRMED, SUPERSEDED, REVERSED)
    and acts as a node in the organizational decision graph.
    """

    __tablename__ = "decisions"

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
    intelligence_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Core content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status: PROPOSED | CONFIRMED | SUPERSEDED | REVERSED | DEPRECATED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CONFIRMED",
        index=True,
    )
    impact_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MEDIUM",
    )  # LOW, MEDIUM, HIGH, CRITICAL

    # Decision maker attribution
    decided_by_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Deterministic fingerprint to avoid duplicates
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Raw evidence segment IDs (stored as JSON for quick lookup)
    evidence_segment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Temporal context
    effective_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    meeting = relationship("Meeting")
    decided_by_user = relationship("User")
    evidence_items = relationship(
        "DecisionEvidence",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    topics = relationship(
        "DecisionTopic",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "DecisionEvent",
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="DecisionEvent.created_at.asc()",
    )

    # Directed graph edges
    outgoing_relationships = relationship(
        "DecisionRelationship",
        foreign_keys="DecisionRelationship.source_decision_id",
        back_populates="source_decision",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "DecisionRelationship",
        foreign_keys="DecisionRelationship.target_decision_id",
        back_populates="target_decision",
        cascade="all, delete-orphan",
    )


class DecisionEvidence(TenantMixin, Base):
    """
    Direct link between an enterprise decision and supporting canonical transcript segments.
    """

    __tablename__ = "decision_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcript_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    decision = relationship("EnterpriseDecision", back_populates="evidence_items")
    segment = relationship("TranscriptSegment")


class DecisionTopic(TenantMixin, Base):
    """
    Semantic topic, entity, or domain tag associated with a decision.
    Used by DecisionResolutionService to track decisions evolving within a domain.
    """

    __tablename__ = "decision_topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    decision = relationship("EnterpriseDecision", back_populates="topics")


class DecisionRelationship(TenantMixin, Base):
    """
    Directed relationship between decisions in the decision graph.
    relationship_type:
      - SUPERSEDES: source overrides/replaces target
      - REVERSES:   source cancels/reverses target
      - REFINES:    source provides added detail/constraint on target
      - RELATED:    source references or correlates with target
    """

    __tablename__ = "decision_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # SUPERSEDES | REVERSES | REFINES | RELATED
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_decision = relationship(
        "EnterpriseDecision",
        foreign_keys=[source_decision_id],
        back_populates="outgoing_relationships",
    )
    target_decision = relationship(
        "EnterpriseDecision",
        foreign_keys=[target_decision_id],
        back_populates="incoming_relationships",
    )


class DecisionEvent(TenantMixin, Base):
    """
    Immutable audit event log capturing every lifecycle change to a decision.
    """

    __tablename__ = "decision_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # CREATED | STATUS_CHANGED | RELATIONSHIP_ADDED | REVISED
    previous_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    decision = relationship("EnterpriseDecision", back_populates="events")
    actor_user = relationship("User")


# Backwards-compatible alias within decisions package
Decision = EnterpriseDecision
