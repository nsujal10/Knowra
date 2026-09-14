from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime

from app.models.base import Base
from app.models.mixins import TenantMixin


class UploadSession(TenantMixin, Base):
    __tablename__ = "upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider_upload_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    parts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    part_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_aborted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )