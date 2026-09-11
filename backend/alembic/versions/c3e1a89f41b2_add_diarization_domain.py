"""add diarization domain

Revision ID: c3e1a89f41b2
Revises: b297bc48e670
Create Date: 2026-09-11 18:30:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e1a89f41b2'
down_revision: Union[str, Sequence[str], None] = 'b297bc48e670'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create speakers table
    op.create_table(
        'speakers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('meeting_id', sa.Uuid(), nullable=False),
        sa.Column('speaker_label', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_speakers_meeting_id'), 'speakers', ['meeting_id'], unique=False)
    op.create_index(op.f('ix_speakers_user_id'), 'speakers', ['user_id'], unique=False)
    op.create_index(op.f('ix_speakers_tenant_id'), 'speakers', ['tenant_id'], unique=False)

    # 2. Create diarization_runs table
    op.create_table(
        'diarization_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('media_asset_id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('provider_name', sa.String(length=100), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('speakers_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['media_asset_id'], ['media_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['processing_jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_diarization_runs_media_asset_id'), 'diarization_runs', ['media_asset_id'], unique=False)
    op.create_index(op.f('ix_diarization_runs_tenant_id'), 'diarization_runs', ['tenant_id'], unique=False)

    # 3. Create speaker_segments table (parallel timeline)
    op.create_table(
        'speaker_segments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('diarization_run_id', sa.Uuid(), nullable=False),
        sa.Column('speaker_id', sa.Uuid(), nullable=False),
        sa.Column('start_seconds', sa.Float(), nullable=False),
        sa.Column('end_seconds', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['diarization_run_id'], ['diarization_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['speaker_id'], ['speakers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_speaker_segments_diarization_run_id'), 'speaker_segments', ['diarization_run_id'], unique=False)
    op.create_index(op.f('ix_speaker_segments_speaker_id'), 'speaker_segments', ['speaker_id'], unique=False)
    op.create_index(op.f('ix_speaker_segments_tenant_id'), 'speaker_segments', ['tenant_id'], unique=False)

    # 4. Add alignment columns to transcript_segments
    op.add_column('transcript_segments', sa.Column('speaker_id', sa.Uuid(), nullable=True))
    op.add_column('transcript_segments', sa.Column('alignment_confidence', sa.Float(), nullable=True))
    op.add_column('transcript_segments', sa.Column('alignment_status', sa.String(length=50), nullable=True))
    op.create_foreign_key(
        'fk_transcript_segments_speaker_id',
        'transcript_segments',
        'speakers',
        ['speaker_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_transcript_segments_speaker_id'), 'transcript_segments', ['speaker_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('fk_transcript_segments_speaker_id', 'transcript_segments', type_='foreignkey')
    op.drop_index(op.f('ix_transcript_segments_speaker_id'), table_name='transcript_segments')
    op.drop_column('transcript_segments', 'alignment_status')
    op.drop_column('transcript_segments', 'alignment_confidence')
    op.drop_column('transcript_segments', 'speaker_id')

    op.drop_index(op.f('ix_speaker_segments_tenant_id'), table_name='speaker_segments')
    op.drop_index(op.f('ix_speaker_segments_speaker_id'), table_name='speaker_segments')
    op.drop_index(op.f('ix_speaker_segments_diarization_run_id'), table_name='speaker_segments')
    op.drop_table('speaker_segments')

    op.drop_index(op.f('ix_diarization_runs_tenant_id'), table_name='diarization_runs')
    op.drop_index(op.f('ix_diarization_runs_media_asset_id'), table_name='diarization_runs')
    op.drop_table('diarization_runs')

    op.drop_index(op.f('ix_speakers_tenant_id'), table_name='speakers')
    op.drop_index(op.f('ix_speakers_user_id'), table_name='speakers')
    op.drop_index(op.f('ix_speakers_meeting_id'), table_name='speakers')
    op.drop_table('speakers')
