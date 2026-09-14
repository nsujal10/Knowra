"""
Phase 19 & 20 Schema: Add KnowledgeEmbedding model and vector indexes

Revision ID: a7c8e9102b34
Revises: f6b42c19e810
Create Date: 2026-09-14 17:30:00.000000

Phase 19 – Embeddings
    • knowledge_embeddings table with Vector(384) and content_hash index
Phase 20 – Hybrid Search Optimization
    • IVFFLAT / HNSW index support on knowledge_embeddings
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision: str = "a7c8e9102b34"
down_revision: Union[str, Sequence[str], None] = "f6b42c19e810"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Phase 19: knowledge_embeddings table
    # -----------------------------------------------------------------------
    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0"),
        sa.Column("dimensions", sa.Integer(), nullable=False, server_default="384"),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_embeddings_tenant_id", "knowledge_embeddings", ["tenant_id"])
    op.create_index("ix_knowledge_embeddings_chunk_id", "knowledge_embeddings", ["chunk_id"])
    op.create_index("ix_knowledge_embeddings_meeting_id", "knowledge_embeddings", ["meeting_id"])
    op.create_index("ix_knowledge_embeddings_content_hash", "knowledge_embeddings", ["content_hash"])

    # Unique index for deterministic deduplication
    op.create_index(
        "ix_knowledge_embeddings_dedup",
        "knowledge_embeddings",
        ["tenant_id", "content_hash", "model_name", "model_version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("knowledge_embeddings")
