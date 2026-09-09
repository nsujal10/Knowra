from app.repositories.base_tenant import BaseTenantRepository
from app.models.meeting import Meeting
from uuid import UUID
from typing import List, Optional

class MeetingRepository(BaseTenantRepository):
    def get_by_id(self, meeting_id: UUID) -> Optional[Meeting]:
        return self.session.query(Meeting).filter(
            Meeting.tenant_id == self.tenant_id,
            Meeting.id == meeting_id
        ).first()

    def list(self, skip: int = 0, limit: int = 20) -> List[Meeting]:
        return self.session.query(Meeting).filter(
            Meeting.tenant_id == self.tenant_id
        ).offset(skip).limit(limit).all()

    def create(self, owner_id: UUID, title: str) -> Meeting:
        meeting = Meeting(tenant_id=self.tenant_id, owner_id=owner_id, title=title)
        self.session.add(meeting)
        self.session.commit()
        self.session.refresh(meeting)
        return meeting

    def update(self, meeting_id: UUID, update_data: dict) -> Optional[Meeting]:
        meeting = self.get_by_id(meeting_id)
        if not meeting:
            return None
        for key, value in update_data.items():
            setattr(meeting, key, value)
        self.session.commit()
        self.session.refresh(meeting)
        return meeting

    def delete(self, meeting_id: UUID) -> bool:
        meeting = self.get_by_id(meeting_id)
        if not meeting:
            return False
        self.session.delete(meeting)
        self.session.commit()
        return True
