"""
Phase 14 – Speaker Identification Models

Design invariants
-----------------
1. SpeakerProfile stores a voice embedding vector (serialised as JSON float list)
   scoped exclusively to a single tenant.  Cross-tenant reads are prohibited.
2. SpeakerIdentityAssignment separates the diarization-cluster identity (speaker_id)
   from the human identity (resolved_user_id / external_participant_name).  The two
   MUST NOT be auto-merged; a human CONFIRMATION event is required.
3. The full assignment history is preserved via SpeakerIdentityHistory so every
   SUGGESTED → CONFIRMED / REJECTED transition is auditable.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class SpeakerProfile(TenantMixin, Base):
    """
    A reusable voice profile for a recurring participant within a single tenant.

    The embedding field holds a normalised float vector (e.g. 256-d) produced by
    the voice-embedding model.  It is intentionally stored as JSON rather than a
    pgvector column so that the schema compiles without the vector extension present.
    Replace with a Vector(256) column when pgvector is provisioned in production.
    """

    __tablename__ = "speaker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    # FK to users.id – only set for internal employees whose identity is confirmed.
    # MUST remain NULL until a human explicitly confirms the match.
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Human-readable label ("Rahul Sharma", "External Vendor", etc.)
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # "INTERNAL_USER" | "EXTERNAL_PARTICIPANT" | "UNKNOWN"
    participant_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNKNOWN",
    )
    # Serialised float list; NULL until at least one voice sample is enrolled.
    embedding_json: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )
    # Model used to generate the embedding (for future re-embedding on model upgrade)
    embedding_model: Mapped[Optional[str]] = mapped_column(
        String(100),
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

    user = relationship("User")
    identity_assignments = relationship(
        "SpeakerIdentityAssignment",
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class SpeakerIdentityAssignment(TenantMixin, Base):
    """
    Bridges a per-meeting diarization speaker cluster (Speaker.id) to a
    SpeakerProfile.  Only ONE active assignment may exist per (speaker_id, tenant_id)
    pair; prior assignments are preserved in SpeakerIdentityHistory.

    Assignment lifecycle
    --------------------
    SUGGESTED  – produced automatically by the voice-matching algorithm.
    CONFIRMED  – a human operator has verified the suggestion via the API.
    REJECTED   – the human operator disagreed; the system must not re-suggest.
    """

    __tablename__ = "speaker_identity_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    # The per-meeting speaker cluster (from diarization)
    speaker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speakers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The resolved long-lived profile (could be INTERNAL_USER or EXTERNAL)
    speaker_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speaker_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "VOICE_MATCH" | "MANUAL" | "SYSTEM"
    assignment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # "SUGGESTED" | "CONFIRMED" | "REJECTED"
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SUGGESTED",
    )
    # Cosine similarity score from the matching engine (NULL for MANUAL)
    similarity_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )
    # User who confirmed or rejected (NULL if still SUGGESTED)
    actioned_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    speaker = relationship("Speaker")
    profile = relationship("SpeakerProfile", back_populates="identity_assignments")
    actioned_by = relationship("User")
    history = relationship(
        "SpeakerIdentityHistory",
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="SpeakerIdentityHistory.created_at",
    )


class SpeakerIdentityHistory(TenantMixin, Base):
    """
    Immutable audit trail: every status transition on SpeakerIdentityAssignment
    appends a row here.  Rows are never updated or deleted.
    """

    __tablename__ = "speaker_identity_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speaker_identity_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The status value AFTER this transition
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Actor who triggered the transition (NULL for system-generated transitions)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Event name for audit log correlation
    event_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    assignment = relationship("SpeakerIdentityAssignment", back_populates="history")
    actor = relationship("User")
