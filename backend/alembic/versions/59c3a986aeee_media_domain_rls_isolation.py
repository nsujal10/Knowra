"""media domain rls isolation

Revision ID: 59c3a986aeee
Revises: 6938da68216e
"""

from typing import Sequence, Union

from alembic import op


revision: str = "59c3a986aeee"
down_revision: Union[str, Sequence[str], None] = "6938da68216e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MEDIA_TABLES = (
    "media_assets",
    "upload_sessions",
    "processing_jobs",
    "media_artifacts",
)


def upgrade() -> None:
    for table in MEDIA_TABLES:
        op.execute(
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"
        )

        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation_policy
            ON {table}
            USING (
                tenant_id = current_setting(
                    'app.current_tenant',
                    true
                )::uuid
            )
            WITH CHECK (
                tenant_id = current_setting(
                    'app.current_tenant',
                    true
                )::uuid
            );
            """
        )


def downgrade() -> None:
    for table in reversed(MEDIA_TABLES):
        op.execute(
            f"""
            DROP POLICY IF EXISTS
            {table}_tenant_isolation_policy
            ON {table};
            """
        )

        op.execute(
            f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"
        )