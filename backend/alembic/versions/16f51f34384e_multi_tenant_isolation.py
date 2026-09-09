"""multi_tenant_isolation

Revision ID: 16f51f34384e
Revises: 9ea02b26c14a
Create Date: 2026-09-09 16:25:27.640383
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16f51f34384e'
down_revision: Union[str, Sequence[str], None] = 'ca09bede1119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.execute("ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY tenant_isolation_policy ON meetings USING (tenant_id = current_setting('app.current_tenant')::uuid);")
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade database schema."""
    op.execute("DROP POLICY tenant_isolation_policy ON meetings;")
    op.execute("ALTER TABLE meetings DISABLE ROW LEVEL SECURITY;")  
    pass
    # ### end Alembic commands ###