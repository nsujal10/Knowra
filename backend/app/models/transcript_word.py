from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.models.base import Base
from app.models.mixins import TenantMixin

class TranscriptWord(TenantMixin, Base):
    __tablename__ = "transcript_words"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transcript_segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transcript_segments.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    segment = relationship("TranscriptSegment", back_populates="words")
