"""
Phase 26 – Enterprise Integrations & Event-Driven Workflow Models (SQLAlchemy 2.0)

Entities:
  - Integration: Configured third-party service connection (Slack, Teams, Jira, Webhooks) with encrypted secrets.
  - IntegrationEvent: Outbound & inbound event records enforcing idempotency via external_event_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
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


class Integration(TenantMixin, Base):
    """
    Enterprise integration channel configuration.
    Stores third-party credentials encrypted via SecretEncryptionService.
    """

    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Provider: SLACK | TEAMS | JIRA | WEBHOOK
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Securely encrypted secret or token (NEVER plaintext)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)

    # Destination configuration
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    channel_or_project_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Event types subscribed to: e.g. ["ACTION_CREATED", "DECISION_CONFIRMED", "MEETING_PROCESSED"]
    events_subscribed: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Status: ACTIVE | INACTIVE | ERROR
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False, index=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

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

    events = relationship("IntegrationEvent", back_populates="integration", cascade="all, delete-orphan")


class IntegrationEvent(TenantMixin, Base):
    """
    Tracks external integration event lifecycles.
    Enforces idempotency using external_event_id to prevent double-firing side effects.
    """

    __tablename__ = "integration_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Direction: OUTBOUND | INBOUND
    direction: Mapped[str] = mapped_column(String(20), default="OUTBOUND", nullable=False, index=True)

    # Unique event identifier for exactly-once processing (idempotency key)
    external_event_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Event Type: ACTION_CREATED | DECISION_CONFIRMED | MEETING_PROCESSED | INBOUND_WEBHOOK
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Status: PENDING | DISPATCHED | COMPLETED | FAILED | DUPLICATE_SKIPPED
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)

    # Retry and resilience metrics
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    response_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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

    integration = relationship("Integration", back_populates="events")

    __table_args__ = (
        Index("ix_integration_events_tenant_external_id", "tenant_id", "external_event_id"),
    )
