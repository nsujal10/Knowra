from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, declared_attr


class TenantMixin:
    """
    Adds tenant ownership to a database entity.

    Every tenant-scoped table must contain:

        tenant_id -> organizations.id
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[UUID]:
        return mapped_column(
            ForeignKey(
                "organizations.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )