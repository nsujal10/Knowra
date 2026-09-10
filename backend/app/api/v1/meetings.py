from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.security.tenant import TenantContext, get_tenant_context
from app.schemas.meeting import MeetingCreate, MeetingResponse
from app.models.meeting import Meeting

router = APIRouter()

@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(data: MeetingCreate, db: Session = Depends(get_db), tenant_ctx: TenantContext = Depends(get_tenant_context)):
    meeting = Meeting(tenant_id=tenant_ctx.tenant_id, owner_id=tenant_ctx.user_id, title=data.title)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting
