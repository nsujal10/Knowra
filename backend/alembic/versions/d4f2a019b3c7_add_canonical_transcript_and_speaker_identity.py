"""add canonical transcript and speaker identity domain

Revision ID: d4f2a019b3c7
Revises: c3e1a89f41b2
Create Date: 2026-09-14 11:15:00.000000

Phase 13 – Canonical Transcript Format
    • transcript_versions  – versioned snapshots with full provenance

Phase 14 – Speaker Identification
    • speaker_profiles              – reusable voice profiles (tenant-scoped)
    • speaker_identity_assignments  – SUGGESTED/CONFIRMED/REJECTED lifecycle
    • speaker_identity_history      – immutable audit trail of status transitions
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "d4f2a019b3c7"
down_revision: Union[str, Sequence[str], None] = "c3e1a89f41b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Phase 13 – transcript_versions
    # -----------------------------------------------------------------------
    op.create_table(
        "transcript_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="AI_GENERATED"),
        sa.Column("edited_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("edit_reason", sa.String(length=1024), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["edited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_versions_transcript_id", "transcript_versions", ["transcript_id"])
    op.create_index("ix_transcript_versions_tenant_id", "transcript_versions", ["tenant_id"])
    # Composite: used for tenant-scoped version lookup
    op.create_index(
        "ix_transcript_versions_tenant_transcript_version",
        "transcript_versions",
        ["tenant_id", "transcript_id", "version_number"],
        unique=True,
    )

    # -----------------------------------------------------------------------
    # Phase 14 – speaker_profiles
    # -----------------------------------------------------------------------
    op.create_table(
        "speaker_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("participant_type", sa.String(length=50), nullable=False, server_default="UNKNOWN"),
        sa.Column("embedding_json", sa.JSON(), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speaker_profiles_tenant_id", "speaker_profiles", ["tenant_id"])
    op.create_index("ix_speaker_profiles_user_id", "speaker_profiles", ["user_id"])

    # -----------------------------------------------------------------------
    # Phase 14 – speaker_identity_assignments
    # -----------------------------------------------------------------------
    op.create_table(
        "speaker_identity_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("speaker_id", sa.Uuid(), nullable=False),
        sa.Column("speaker_profile_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_method", sa.String(length=50), nullable=False),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="SUGGESTED"),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("actioned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_id"], ["speakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_profile_id"], ["speaker_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actioned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speaker_identity_assignments_tenant_id", "speaker_identity_assignments", ["tenant_id"])
    op.create_index("ix_speaker_identity_assignments_speaker_id", "speaker_identity_assignments", ["speaker_id"])
    op.create_index("ix_speaker_identity_assignments_speaker_profile_id", "speaker_identity_assignments", ["speaker_profile_id"])
    op.create_index("ix_speaker_identity_assignments_actioned_by_user_id", "speaker_identity_assignments", ["actioned_by_user_id"])
    # Composite for tenant-scoped speaker assignment queries
    op.create_index(
        "ix_speaker_identity_assignments_tenant_speaker",
        "speaker_identity_assignments",
        ["tenant_id", "speaker_id"],
    )

    # -----------------------------------------------------------------------
    # Phase 14 – speaker_identity_history  (immutable audit trail)
    # -----------------------------------------------------------------------
    op.create_table(
        "speaker_identity_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            index=True,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["speaker_identity_assignments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speaker_identity_history_assignment_id", "speaker_identity_history", ["assignment_id"])
    op.create_index("ix_speaker_identity_history_tenant_id", "speaker_identity_history", ["tenant_id"])
    op.create_index("ix_speaker_identity_history_created_at", "speaker_identity_history", ["created_at"])


def downgrade() -> None:
    # speaker_identity_history
    op.drop_index("ix_speaker_identity_history_created_at", table_name="speaker_identity_history")
    op.drop_index("ix_speaker_identity_history_tenant_id", table_name="speaker_identity_history")
    op.drop_index("ix_speaker_identity_history_assignment_id", table_name="speaker_identity_history")
    op.drop_table("speaker_identity_history")

    # speaker_identity_assignments
    op.drop_index("ix_speaker_identity_assignments_tenant_speaker", table_name="speaker_identity_assignments")
    op.drop_index("ix_speaker_identity_assignments_actioned_by_user_id", table_name="speaker_identity_assignments")
    op.drop_index("ix_speaker_identity_assignments_speaker_profile_id", table_name="speaker_identity_assignments")
    op.drop_index("ix_speaker_identity_assignments_speaker_id", table_name="speaker_identity_assignments")
    op.drop_index("ix_speaker_identity_assignments_tenant_id", table_name="speaker_identity_assignments")
    op.drop_table("speaker_identity_assignments")

    # speaker_profiles
    op.drop_index("ix_speaker_profiles_user_id", table_name="speaker_profiles")
    op.drop_index("ix_speaker_profiles_tenant_id", table_name="speaker_profiles")
    op.drop_table("speaker_profiles")

    # transcript_versions
    op.drop_index("ix_transcript_versions_tenant_transcript_version", table_name="transcript_versions")
    op.drop_index("ix_transcript_versions_tenant_id", table_name="transcript_versions")
    op.drop_index("ix_transcript_versions_transcript_id", table_name="transcript_versions")
    op.drop_table("transcript_versions")
