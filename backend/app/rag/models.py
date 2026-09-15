"""
Phase 22 – Conversational RAG Chat Models (SQLAlchemy 2.0)

Entities:
  - ChatConversation: Persistent conversation thread bound to tenant and user, optionally scoped to a meeting.
  - ChatMessage: Individual interaction turn with query rewriting audit, intent classification, and verified citations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class ChatConversation(TenantMixin, Base):
    """
    Persistent chat thread owned by a user within an enterprise tenant.
    Optionally scoped to a specific meeting_id for targeted question answering.
    """

    __tablename__ = "chat_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Conversation",
    )
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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

    # Relationships
    messages: Mapped[List[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()",
    )
    user = relationship("User")
    meeting = relationship("Meeting")


class ChatMessage(TenantMixin, Base):
    """
    Individual message turn in a conversational thread.
    Records intent classification, rewritten query, and verified citation evidence.
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="USER",  # USER | ASSISTANT | SYSTEM
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Conversational Orchestration Metadata
    intent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    rewritten_query: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    citations_json: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    retrieval_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    conversation: Mapped[ChatConversation] = relationship(
        "ChatConversation",
        back_populates="messages",
    )
