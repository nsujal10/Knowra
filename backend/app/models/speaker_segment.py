import uuid
from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class SpeakerSegment(TenantMixin, Base):
    __tablename__ = "speaker_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    diarization_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("diarization_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speakers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    end_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    run = relationship("DiarizationRun", back_populates="segments")
    speaker = relationship("Speaker", back_populates="speaker_segments")
