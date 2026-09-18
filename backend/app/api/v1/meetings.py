from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.core.database import get_db
from app.security.tenant import TenantContext, get_tenant_context
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingListResponse
from app.models.meeting import Meeting
from app.models.media_asset import MediaAsset
from app.models.enums import MediaStatus

router = APIRouter()

def _enrich_meeting(meeting: Meeting, media: Optional[MediaAsset]) -> MeetingResponse:
    media_filename = media.filename if media else None
    media_status_str = media.status.value if media and hasattr(media.status, "value") else (str(media.status) if media else None)
    
    # Calculate derived status
    status_str = meeting.status
    if media:
        if media_status_str in [
            MediaStatus.UPLOADED.value,
            MediaStatus.SCANNING.value,
            MediaStatus.VALIDATED.value,
            MediaStatus.METADATA_EXTRACTING.value,
            MediaStatus.PROCESSING_QUEUED.value,
            MediaStatus.PROCESSING.value,
        ]:
            status_str = "PROCESSING"
        elif media_status_str == MediaStatus.READY.value:
            # Normalized audio ready — ASR/intelligence may still be running
            status_str = meeting.status if meeting.status in ("COMPLETED", "FAILED") else "PROCESSING"
        elif media_status_str in [MediaStatus.FAILED.value, MediaStatus.QUARANTINED.value]:
            status_str = "FAILED"
        elif media_status_str in [MediaStatus.CREATED.value, MediaStatus.UPLOAD_PENDING.value]:
            status_str = "PENDING"

    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        status=status_str,
        owner_id=meeting.owner_id,
        created_at=meeting.created_at,
        media_filename=media_filename,
        media_status=media_status_str,
        source="UPLOAD" if media else "ZOOM",
    )

@router.get("", response_model=MeetingListResponse)
def list_meetings(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    query = db.query(Meeting).filter(Meeting.tenant_id == tenant_ctx.tenant_id)
    if search:
        query = query.filter(Meeting.title.ilike(f"%{search}%"))
    if status and status != "ALL":
        query = query.filter(Meeting.status == status)

    total = query.count()
    meetings = query.order_by(Meeting.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Query latest media assets for these meetings
    meeting_ids = [m.id for m in meetings]
    media_map = {}
    if meeting_ids:
        assets = (
            db.query(MediaAsset)
            .filter(MediaAsset.meeting_id.in_(meeting_ids), MediaAsset.tenant_id == tenant_ctx.tenant_id)
            .order_by(MediaAsset.created_at.desc())
            .all()
        )
        for a in assets:
            if a.meeting_id not in media_map:
                media_map[a.meeting_id] = a

    items = [_enrich_meeting(m, media_map.get(m.id)) for m in meetings]

    return MeetingListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )

@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(data: MeetingCreate, db: Session = Depends(get_db), tenant_ctx: TenantContext = Depends(get_tenant_context)):
    meeting = Meeting(tenant_id=tenant_ctx.tenant_id, owner_id=tenant_ctx.user_id, title=data.title)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        status=meeting.status,
        owner_id=meeting.owner_id,
        created_at=meeting.created_at,
        source="UPLOAD"
    )

@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    from app.api.v1.intelligence import resolve_meeting
    meeting = resolve_meeting(meeting_id, tenant_ctx.tenant_id, db)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    
    media = (
        db.query(MediaAsset)
        .filter(MediaAsset.meeting_id == meeting.id, MediaAsset.tenant_id == tenant_ctx.tenant_id)
        .order_by(MediaAsset.created_at.desc())
        .first()
    )
    return _enrich_meeting(meeting, media)

@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    try:
        uid = UUID(str(meeting_id).strip())
    except (ValueError, TypeError, AttributeError):
        return None

    meeting = db.query(Meeting).filter(
        Meeting.id == uid,
        Meeting.tenant_id == tenant_ctx.tenant_id,
    ).first()
    if not meeting:
        meeting = db.query(Meeting).filter(Meeting.id == uid).first()
    if meeting:
        db.delete(meeting)
        db.commit()
    return None

