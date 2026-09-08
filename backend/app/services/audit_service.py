from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository

class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(self, action: str, user_id=None, org_id=None, success=True, metadata_json=None):
        log = AuditLog(
            action=action,
            user_id=user_id,
            organization_id=org_id,
            success=success,
            metadata_json=metadata_json
        )
        self.repo.create(log)
