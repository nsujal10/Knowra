from typing import Generator
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.tenant import TenantContext, get_tenant_context


def get_tenant_db(
    db: Session = Depends(get_db),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Generator[Session, None, None]:
    """
    Provide a SQLAlchemy session with PostgreSQL RLS tenant context configured.

    PostgreSQL RLS policies use:

        current_setting('app.current_tenant')

    to determine which tenant's rows are accessible.

    SET LOCAL is intentionally used so that the tenant setting exists only
    for the current database transaction.
    """

    try:
        # Start an explicit transaction.

        if not db.in_transaction():
            db.begin()

        # Set tenant context for THIS transaction only.
        #
        # The parameterized form prevents SQL injection and correctly
        # handles UUID values.

        db.execute(
            text("SET LOCAL app.current_tenant = :tenant_id"),
            {
                "tenant_id": str(tenant_context.tenant_id),
            },
        )

        yield db

    except Exception:
        db.rollback()
        raise

    finally:
        # SET LOCAL automatically disappears when the transaction ends.
        #
        # Explicit rollback guarantees that the connection returned to
        # SQLAlchemy's pool cannot retain an active transaction/context.

        if db.in_transaction():
            db.rollback()