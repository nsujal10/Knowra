from sqlalchemy.orm import Session
from uuid import UUID
from fastapi import HTTPException
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import MeetingCreate, MeetingUpdate

class MeetingService:
    def __init__(self, db: Session, tenant_id: UUID, user_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = MeetingRepository(db, tenant_id)

    def get_meeting(self, meeting_id: UUID):
        meeting = self.repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        return meeting

    def list_meetings(self, skip: int = 0, limit: int = 20):
        return self.repo.list(skip, limit)

    def create_meeting(self, data: MeetingCreate):
        return self.repo.create(owner_id=self.user_id, title=data.title)

    def update_meeting(self, meeting_id: UUID, data: MeetingUpdate):
        meeting = self.repo.update(meeting_id, data.model_dump(exclude_unset=True))
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        return meeting

    def delete_meeting(self, meeting_id: UUID):
        success = self.repo.delete(meeting_id)
        if not success:
            raise HTTPException(status_code=404, detail="Meeting not found")
