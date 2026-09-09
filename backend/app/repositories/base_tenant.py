from sqlalchemy.orm import Session
from uuid import UUID

class BaseTenantRepository:
    """
    Base repository enforcing tenant_id requirement on instantiation.
    """
    def __init__(self, session: Session, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id
