import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user_id"),
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'google' | 'microsoft'
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # OIDC 'sub' claim
    provider_email: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="identities")
