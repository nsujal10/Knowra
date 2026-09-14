"""add decision intelligence and knowledge chunking schema

Revision ID: f6b42c19e810
Revises: e5a31b8f1024
Create Date: 2026-09-14 16:00:00.000000

Phase 17 – Decision Intelligence
    • decisions (upgrade table with title, status, fingerprint, etc.)
    • decision_evidence
    • decision_topics
    • decision_relationships
    • decision_events

Phase 18 – Knowledge Chunking & Hybrid Retrieval
    • knowledge_chunks (pgvector Vector(384) + tsvector)
    • knowledge_chunk_segments
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision: str = "f6b42c19e810"
down_revision: Union[str, Sequence[str], None] = "e5a31b8f1024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Ensure pgvector extension is created
    # -----------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # -----------------------------------------------------------------------
    # Phase 17: decisions table alterations
    # -----------------------------------------------------------------------
    op.add_column("decisions", sa.Column("title", sa.String(length=255), nullable=False, server_default="Untitled Decision"))
    op.add_column("decisions", sa.Column("status", sa.String(length=50), nullable=False, server_default="CONFIRMED"))
    op.add_column("decisions", sa.Column("decided_by_user_id", sa.Uuid(), nullable=True))
    op.add_column("decisions", sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("decisions", sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("decisions", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))

    op.create_foreign_key("fk_decisions_decided_by_user_id", "decisions", "users", ["decided_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_decisions_status", "decisions", ["status"])
    op.create_index("ix_decisions_fingerprint", "decisions", ["fingerprint"])

    # decision_evidence
    op.create_table(
        "decision_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["transcript_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_evidence_tenant_id", "decision_evidence", ["tenant_id"])
    op.create_index("ix_decision_evidence_decision_id", "decision_evidence", ["decision_id"])
    op.create_index("ix_decision_evidence_segment_id", "decision_evidence", ["segment_id"])

    # decision_topics
    op.create_table(
        "decision_topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("topic_name", sa.String(length=100), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_topics_tenant_id", "decision_topics", ["tenant_id"])
    op.create_index("ix_decision_topics_decision_id", "decision_topics", ["decision_id"])
    op.create_index("ix_decision_topics_topic_name", "decision_topics", ["topic_name"])

    # decision_relationships
    op.create_table(
        "decision_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source_decision_id", sa.Uuid(), nullable=False),
        sa.Column("target_decision_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_relationships_tenant_id", "decision_relationships", ["tenant_id"])
    op.create_index("ix_decision_relationships_source_id", "decision_relationships", ["source_decision_id"])
    op.create_index("ix_decision_relationships_target_id", "decision_relationships", ["target_decision_id"])
    op.create_index("ix_decision_relationships_type", "decision_relationships", ["relationship_type"])

    # decision_events
    op.create_table(
        "decision_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_state", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("new_state", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_events_tenant_id", "decision_events", ["tenant_id"])
    op.create_index("ix_decision_events_decision_id", "decision_events", ["decision_id"])

    # -----------------------------------------------------------------------
    # Phase 18: knowledge_chunks & knowledge_chunk_segments
    # -----------------------------------------------------------------------
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_topic", sa.String(length=255), nullable=True),
        sa.Column("topic_tags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("speaker_names", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("end_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_tenant_id", "knowledge_chunks", ["tenant_id"])
    op.create_index("ix_knowledge_chunks_meeting_id", "knowledge_chunks", ["meeting_id"])
    op.create_index("ix_knowledge_chunks_primary_topic", "knowledge_chunks", ["primary_topic"])

    # Full text search GIN index on knowledge chunks
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_content_fts ON knowledge_chunks USING gin(to_tsvector('english', content));"
    )

    # knowledge_chunk_segments
    op.create_table(
        "knowledge_chunk_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_in_chunk", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["transcript_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunk_segments_tenant_id", "knowledge_chunk_segments", ["tenant_id"])
    op.create_index("ix_knowledge_chunk_segments_chunk_id", "knowledge_chunk_segments", ["chunk_id"])
    op.create_index("ix_knowledge_chunk_segments_segment_id", "knowledge_chunk_segments", ["segment_id"])


def downgrade() -> None:
    op.drop_table("knowledge_chunk_segments")
    op.drop_table("knowledge_chunks")
    op.drop_table("decision_events")
    op.drop_table("decision_relationships")
    op.drop_table("decision_topics")
    op.drop_table("decision_evidence")
    op.drop_constraint("fk_decisions_decided_by_user_id", "decisions", type_="foreignkey")
    op.drop_column("decisions", "updated_at")
    op.drop_column("decisions", "effective_date")
    op.drop_column("decisions", "fingerprint")
    op.drop_column("decisions", "decided_by_user_id")
    op.drop_column("decisions", "status")
    op.drop_column("decisions", "title")
