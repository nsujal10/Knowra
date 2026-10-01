from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
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

    is_transcript = bool(
        media and media.filename and any(media.filename.lower().endswith(ext) for ext in [".txt", ".srt", ".vtt"])
    )
    source_val = "TRANSCRIPT_IMPORT" if is_transcript else ("UPLOAD" if media else "ZOOM")

    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        status=status_str,
        owner_id=meeting.owner_id,
        created_at=meeting.created_at,
        media_filename=media_filename,
        media_status=media_status_str,
        source=source_val,
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
    effective_title = data.title.strip() if data.title and data.title.strip() else "Untitled Meeting"
    meeting = Meeting(tenant_id=tenant_ctx.tenant_id, owner_id=tenant_ctx.user_id, title=effective_title)
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

@router.post("/import-transcript", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def import_transcript_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    language: Optional[str] = Form("en"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Directly import an existing .txt, .srt, or .vtt transcript file.
    Bypasses Whisper speech-to-text, parses speakers & timestamps,
    and runs full AI intelligence extraction and RAG indexing.
    """
    filename = file.filename or "transcript.txt"
    lower_fn = filename.lower()
    if not any(lower_fn.endswith(ext) for ext in [".txt", ".srt", ".vtt"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported transcript format. Allowed formats: .txt, .srt, .vtt",
        )

    try:
        content_bytes = await file.read()
        content_text = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read transcript file: {str(e)}",
        )

    parsed_date = None
    if meeting_date:
        try:
            parsed_date = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
        except Exception:
            pass

    from app.services.transcript_import_service import TranscriptImportService

    importer = TranscriptImportService(
        db=db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )

    try:
        meeting = importer.import_from_text(
            filename=filename,
            content=content_text,
            title=title,
            meeting_date=parsed_date,
            language=language or "en",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process transcript: {str(e)}",
        )

    media = (
        db.query(MediaAsset)
        .filter(MediaAsset.meeting_id == meeting.id, MediaAsset.tenant_id == tenant_ctx.tenant_id)
        .order_by(MediaAsset.created_at.desc())
        .first()
    )

    return _enrich_meeting(meeting, media)

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


@router.patch("/{meeting_id}/speakers/{speaker_id}")
def update_meeting_speaker(
    meeting_id: str,
    speaker_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    """Updates the display name of a speaker for this meeting."""
    from app.models.speaker import Speaker
    from app.api.v1.intelligence import resolve_meeting
    meeting = resolve_meeting(meeting_id, tenant_ctx.tenant_id, db)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    new_name = payload.get("displayName") or payload.get("display_name")
    if not new_name or not new_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="displayName is required")
    new_name = new_name.strip()

    speaker = None
    try:
        spk_uuid = UUID(speaker_id)
        speaker = db.query(Speaker).filter(
            Speaker.id == spk_uuid,
            Speaker.meeting_id == meeting.id,
        ).first()
    except (ValueError, TypeError):
        pass

    if not speaker:
        speaker = db.query(Speaker).filter(
            Speaker.meeting_id == meeting.id,
            (Speaker.speaker_label == speaker_id) | (Speaker.display_name == speaker_id),
        ).first()

    if not speaker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker not found")

    speaker.display_name = new_name
    db.commit()
    db.refresh(speaker)

    # Sync live session if active
    from app.services.live_meeting_service import LiveMeetingManager
    manager = LiveMeetingManager.get_instance()
    session = manager.get_session(meeting.id)
    if session:
        for ch in session.channels.values():
            if ch.speaker_id == speaker.id or ch.speaker_label == speaker.speaker_label:
                ch.display_name = new_name

    return {
        "id": str(speaker.id),
        "meetingId": str(meeting.id),
        "speakerLabel": speaker.speaker_label,
        "displayName": speaker.display_name,
    }


@router.post("/{meeting_id}/auto-title", summary="Auto-generate meeting title from transcript")
def auto_title_meeting_endpoint(
    meeting_id: str,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    from app.api.v1.intelligence import resolve_meeting
    from app.services.meeting_title_service import MeetingTitleService
    meeting = resolve_meeting(meeting_id, tenant_ctx.tenant_id, db)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    new_title = MeetingTitleService.auto_title_meeting(db, meeting.id, force=True)
    return {
        "meetingId": str(meeting.id),
        "title": new_title or meeting.title,
        "updated": bool(new_title and new_title != meeting.title),
    }


@router.post("/auto-title/backfill", summary="Backfill intelligent titles for all generic meetings")
def backfill_generic_meeting_titles(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    from app.services.meeting_title_service import MeetingTitleService
    results = MeetingTitleService.backfill_all_generic_titles(db, tenant_id=tenant_ctx.tenant_id)
    return results

