from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.tenant_db import get_tenant_db
from app.security.tenant import TenantContext, get_tenant_context
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse
from app.services.meeting_service import MeetingService

router = APIRouter()

def get_meeting_service(db: Session = Depends(get_tenant_db), tenant_ctx: TenantContext = Depends(get_tenant_context)):
    return MeetingService(db, tenant_ctx.tenant_id, tenant_ctx.user_id)

@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(data: MeetingCreate, svc: MeetingService = Depends(get_meeting_service)):
    return svc.create_meeting(data)

@router.get("", response_model=List[MeetingResponse])
def list_meetings(skip: int = 0, limit: int = 20, svc: MeetingService = Depends(get_meeting_service)):
    return svc.list_meetings(skip, limit)

@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: UUID, svc: MeetingService = Depends(get_meeting_service)):
    return svc.get_meeting(meeting_id)

@router.patch("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(meeting_id: UUID, data: MeetingUpdate, svc: MeetingService = Depends(get_meeting_service)):
    return svc.update_meeting(meeting_id, data)

@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: UUID, svc: MeetingService = Depends(get_meeting_service)):
    svc.delete_meeting(meeting_id)
