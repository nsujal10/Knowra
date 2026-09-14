from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime
from app.models.base import Base
from app.models.mixins import TenantMixin
from app.models.enums import MediaStatus

class MediaAsset(TenantMixin, Base):
    __tablename__ = "media_assets"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[MediaStatus] = mapped_column(
    Enum(
            MediaStatus,
            name="media_status",
            native_enum=True,
        ),
        nullable=False,
        default=MediaStatus.CREATED,
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    video_codec: Mapped[str] = mapped_column(String(100), nullable=True)
    audio_codec: Mapped[str] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
