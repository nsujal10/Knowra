from app.repositories.base import BaseRepository
from app.models.audit_log import AuditLog

class AuditRepository(BaseRepository):
    def create(self, log: AuditLog):
        self.session.add(log)
        self.session.commit()
