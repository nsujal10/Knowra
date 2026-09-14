from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import uuid
from app.models.base import Base
from app.models.mixins import TenantMixin

class TranscriptSegment(TenantMixin, Base):
    __tablename__ = "transcript_segments"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transcript_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Phase 12 Alignment fields
    speaker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("speakers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alignment_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alignment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    transcript = relationship("Transcript", back_populates="segments")
    speaker = relationship("Speaker", back_populates="transcript_segments")
    words = relationship("TranscriptWord", back_populates="segment", cascade="all, delete-orphan", order_by="TranscriptWord.sequence_number")
