from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime

from app.models.base import Base
from app.models.mixins import TenantMixin
from app.models.enums import ArtifactType


class MediaArtifact(TenantMixin, Base):
    __tablename__ = "media_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(
            ArtifactType,
            name="artifact_type",
            native_enum=True,
        ),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    byte_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )