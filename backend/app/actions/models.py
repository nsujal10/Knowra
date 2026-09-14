import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantMixin


class ActionItem(TenantMixin, Base):
    """
    Action item extracted from meeting transcripts or created manually.
    Enforces candidate-vs-truth workflow where AI suggestions start in REVIEW_REQUIRED
    and transition to OPEN upon confirmation.
    """
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    intelligence_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelligence_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow state machine: REVIEW_REQUIRED -> OPEN -> IN_PROGRESS -> COMPLETED / CANCELLED
    status: Mapped[str] = mapped_column(String(50), default="REVIEW_REQUIRED", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)

    # Temporal resolution
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Candidate vs. Truth owner mapping
    owner_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_candidate_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    owner_candidate_speaker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("speakers.id", ondelete="SET NULL"), nullable=True
    )
    owner_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Deterministic fingerprint hash for deduplication during retries
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    evidence_items: Mapped[List["ActionItemEvidence"]] = relationship(
        "ActionItemEvidence", back_populates="action_item", cascade="all, delete-orphan"
    )
    events: Mapped[List["ActionItemEvent"]] = relationship(
        "ActionItemEvent", back_populates="action_item", cascade="all, delete-orphan", order_by="ActionItemEvent.created_at"
    )
    comments: Mapped[List["ActionItemComment"]] = relationship(
        "ActionItemComment", back_populates="action_item", cascade="all, delete-orphan", order_by="ActionItemComment.created_at"
    )

    __table_args__ = (
        Index("ix_action_items_tenant_meeting_fingerprint", "tenant_id", "meeting_id", "fingerprint_hash"),
        Index("ix_action_items_tenant_status", "tenant_id", "status"),
    )


class ActionItemEvidence(TenantMixin, Base):
    """
    Traceability anchor connecting an action item directly to the transcript segment(s)
    from which it was derived.
    """
    __tablename__ = "action_item_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcript_segments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    action_item: Mapped["ActionItem"] = relationship("ActionItem", back_populates="evidence_items")


class ActionItemEvent(TenantMixin, Base):
    """
    Immutable audit history log tracking every lifecycle change, reassignment,
    and state transition of an action item.
    """
    __tablename__ = "action_item_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATED, CONFIRMED, STATUS_CHANGED, REASSIGNED
    previous_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    action_item: Mapped["ActionItem"] = relationship("ActionItem", back_populates="events")


class ActionItemComment(TenantMixin, Base):
    """
    Collaboration comments on action items.
    """
    __tablename__ = "action_item_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    action_item: Mapped["ActionItem"] = relationship("ActionItem", back_populates="comments")
