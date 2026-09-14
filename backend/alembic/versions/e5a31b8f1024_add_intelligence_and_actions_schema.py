"""add intelligence and actions schema

Revision ID: e5a31b8f1024
Revises: d4f2a019b3c7
Create Date: 2026-09-14 14:40:00.000000

Phase 15 – Meeting Intelligence
    • intelligence_runs
    • topics
    • decisions
    • risks
    • questions
    • commitments

Phase 16 – Action Items & Lifecycle
    • action_items
    • action_item_evidence
    • action_item_events
    • action_item_comments
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e5a31b8f1024"
down_revision: Union[str, Sequence[str], None] = "d4f2a019b3c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Phase 15: intelligence_runs
    # -----------------------------------------------------------------------
    op.create_table(
        "intelligence_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intelligence_runs_tenant_id", "intelligence_runs", ["tenant_id"])
    op.create_index("ix_intelligence_runs_meeting_id", "intelligence_runs", ["meeting_id"])
    op.create_index("ix_intelligence_runs_idempotency_key", "intelligence_runs", ["idempotency_key"], unique=True)

    # topics
    op.create_table(
        "topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("intelligence_run_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("start_seconds", sa.Float(), nullable=True),
        sa.Column("end_seconds", sa.Float(), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=True),
        sa.Column("evidence_segment_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intelligence_run_id"], ["intelligence_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topics_tenant_id", "topics", ["tenant_id"])
    op.create_index("ix_topics_meeting_id", "topics", ["meeting_id"])

    # decisions
    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("intelligence_run_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("impact_level", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("decided_by_raw", sa.String(length=255), nullable=True),
        sa.Column("evidence_segment_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intelligence_run_id"], ["intelligence_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisions_tenant_id", "decisions", ["tenant_id"])
    op.create_index("ix_decisions_meeting_id", "decisions", ["meeting_id"])

    # risks
    op.create_table(
        "risks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("intelligence_run_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("evidence_segment_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intelligence_run_id"], ["intelligence_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risks_tenant_id", "risks", ["tenant_id"])
    op.create_index("ix_risks_meeting_id", "risks", ["meeting_id"])

    # questions
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("intelligence_run_id", sa.Uuid(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("asked_by_raw", sa.String(length=255), nullable=True),
        sa.Column("is_answered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("evidence_segment_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intelligence_run_id"], ["intelligence_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_questions_tenant_id", "questions", ["tenant_id"])
    op.create_index("ix_questions_meeting_id", "questions", ["meeting_id"])

    # commitments
    op.create_table(
        "commitments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("intelligence_run_id", sa.Uuid(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("made_by_raw", sa.String(length=255), nullable=True),
        sa.Column("evidence_segment_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intelligence_run_id"], ["intelligence_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commitments_tenant_id", "commitments", ["tenant_id"])
    op.create_index("ix_commitments_meeting_id", "commitments", ["meeting_id"])

    # -----------------------------------------------------------------------
    # Phase 16: action_items
    # -----------------------------------------------------------------------
    op.create_table(
        "action_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("intelligence_run_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="REVIEW_REQUIRED"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date_raw", sa.String(length=255), nullable=True),
        sa.Column("owner_raw", sa.String(length=255), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("owner_candidate_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_candidate_speaker_id", sa.Uuid(), nullable=True),
        sa.Column("owner_confidence", sa.Float(), nullable=True),
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["intelligence_run_id"], ["intelligence_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_candidate_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_candidate_speaker_id"], ["speakers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_items_tenant_id", "action_items", ["tenant_id"])
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"])
    op.create_index("ix_action_items_status", "action_items", ["status"])
    op.create_index("ix_action_items_fingerprint_hash", "action_items", ["fingerprint_hash"])
    op.create_index("ix_action_items_tenant_meeting_fingerprint", "action_items", ["tenant_id", "meeting_id", "fingerprint_hash"])
    op.create_index("ix_action_items_tenant_status", "action_items", ["tenant_id", "status"])

    # action_item_evidence
    op.create_table(
        "action_item_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("action_item_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["action_item_id"], ["action_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["transcript_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_item_evidence_tenant_id", "action_item_evidence", ["tenant_id"])
    op.create_index("ix_action_item_evidence_action_item_id", "action_item_evidence", ["action_item_id"])

    # action_item_events
    op.create_table(
        "action_item_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("action_item_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_state", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("new_state", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["action_item_id"], ["action_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_item_events_tenant_id", "action_item_events", ["tenant_id"])
    op.create_index("ix_action_item_events_action_item_id", "action_item_events", ["action_item_id"])

    # action_item_comments
    op.create_table(
        "action_item_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("action_item_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["action_item_id"], ["action_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_item_comments_tenant_id", "action_item_comments", ["tenant_id"])
    op.create_index("ix_action_item_comments_action_item_id", "action_item_comments", ["action_item_id"])


def downgrade() -> None:
    op.drop_table("action_item_comments")
    op.drop_table("action_item_events")
    op.drop_table("action_item_evidence")
    op.drop_table("action_items")
    op.drop_table("commitments")
    op.drop_table("questions")
    op.drop_table("risks")
    op.drop_table("decisions")
    op.drop_table("topics")
    op.drop_table("intelligence_runs")
