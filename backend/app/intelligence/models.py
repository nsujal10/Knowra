"""
Phase 15 – Meeting Intelligence Models (SQLAlchemy 2.0)

Entities:
  - IntelligenceRun: Tracking header for an LLM analysis execution (idempotency, tokens, version)
  - Topic: High-level themes and discussions with start/end bounds and evidence
  - Decision: Definite agreements or conclusions reached during the meeting
  - Risk: Identified blockers, concerns, or potential pitfalls with severity ratings
  - Question: Significant inquiries, identifying asker, status, and resolved answers
  - Commitment: Promises made by individuals to perform specific obligations
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class IntelligenceRun(TenantMixin, Base):
    """
    Header record representing an execution of the meeting intelligence pipeline.
    Carries provenance (transcript version, provider, model) and deduplication keys.
    """

    __tablename__ = "intelligence_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The transcript version analyzed
    transcript_version_number: Mapped[int] = mapped_column(
        "transcript_version",
        Integer,
        nullable=False,
        default=1,
    )
    # Pipeline status: PENDING | PROCESSING | COMPLETED | FAILED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )
    # AI Provider & Model details
    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="mock",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="mock-llm",
    )
    # Token usage & performance metrics
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deterministic fingerprint to prevent duplicate runs on retry
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
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
    topics = relationship("Topic", back_populates="run", cascade="all, delete-orphan")
    decisions = relationship("app.intelligence.models.Decision", back_populates="run", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="run", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="run", cascade="all, delete-orphan")
    commitments = relationship("Commitment", back_populates="run", cascade="all, delete-orphan")


class Topic(TenantMixin, Base):
    """Extracted meeting theme or agenda discussion topic."""

    __tablename__ = "meeting_topics"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    start_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Cross-validated transcript segment IDs supporting this topic
    evidence_segment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run = relationship("IntelligenceRun", back_populates="topics")
    meeting = relationship("Meeting")


class Decision(TenantMixin, Base):
    """Explicit decision made during the meeting."""

    __tablename__ = "meeting_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact_level: Mapped[str] = mapped_column(String(50), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH
    decided_by_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Cross-validated segment IDs
    evidence_segment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run = relationship("IntelligenceRun", back_populates="decisions")
    meeting = relationship("Meeting")
    decided_by_user = relationship("User")


class Risk(TenantMixin, Base):
    """Potential pitfall, dependency, or identified risk."""

    __tablename__ = "meeting_risks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="IDENTIFIED")  # IDENTIFIED, MITIGATED, ACCEPTED

    evidence_segment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run = relationship("IntelligenceRun", back_populates="risks")
    meeting = relationship("Meeting")


class Question(TenantMixin, Base):
    """Important inquiry raised in the meeting."""

    __tablename__ = "meeting_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    asked_by_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    asked_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_segment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run = relationship("IntelligenceRun", back_populates="questions")
    meeting = relationship("Meeting")
    asked_by_user = relationship("User")


class Commitment(TenantMixin, Base):
    """Formal declaration or commitment pledged during the discussion."""

    __tablename__ = "meeting_commitments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    made_by_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    made_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    evidence_segment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run = relationship("IntelligenceRun", back_populates="commitments")
    meeting = relationship("Meeting")
    made_by_user = relationship("User")
