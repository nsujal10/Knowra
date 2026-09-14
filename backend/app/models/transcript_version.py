"""
Phase 13 – Transcript Versioning Model

Every canonical transcript is mutable by humans (corrections, speaker-label edits).
To preserve AI provenance and support audit, EVERY edit creates a new TranscriptVersion
row.  The parent Transcript.current_version_number always points at the latest version.
The original AI output is version 1 and MUST NOT be deleted.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class TranscriptVersion(TenantMixin, Base):
    __tablename__ = "transcript_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Monotonically increasing.  Version 1 = raw AI output (immutable).
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    # "AI_GENERATED" | "HUMAN_EDITED"
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="AI_GENERATED",
    )
    # Optional: who made the edit (NULL for the initial AI version)
    edited_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Free-text reason (e.g. "Corrected speaker attribution for segment 3")
    edit_reason: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    # Snapshot of the full canonical transcript payload at this version.
    # Stored as JSONB so the entire state is self-contained for replay/audit.
    snapshot_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transcript = relationship("Transcript", back_populates="versions")
    editor = relationship("User")
