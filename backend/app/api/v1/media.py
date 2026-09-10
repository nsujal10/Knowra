from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import math
from datetime import timedelta

from app.core.database import get_db
from app.security.tenant import TenantContext, get_tenant_context
from app.schemas.media import MediaUploadRequest, MediaUploadResponse, PartUrl, MediaCompleteRequest, MediaStatusResponse
from app.models.meeting import Meeting
from app.models.media_asset import MediaAsset
from app.models.upload_session import UploadSession
from app.models.enums import MediaStatus
from app.storage.minio import get_storage_client, ObjectStorage
from app.storage.service import StorageService
from app.media.validation import validate_mime_type

# Absolute minimum import for Celery to avoid circular loops
from app.workers.media_pipeline import trigger_media_pipeline


router = APIRouter()

@router.post("/meetings/{meeting_id}/media", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
def init_media_upload(
    meeting_id: UUID, 
    req: MediaUploadRequest, 
    db: Session = Depends(get_db), 
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    storage: ObjectStorage = Depends(get_storage_client)
):
    if not validate_mime_type(req.content_type):
        raise HTTPException(status_code=400, detail="Unsupported MIME type")
        
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.tenant_id == tenant_ctx.tenant_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    ext = req.filename.split(".")[-1] if "." in req.filename else "bin"
    
    media = MediaAsset(
    tenant_id=tenant_ctx.tenant_id,
    meeting_id=meeting.id,
    filename=req.filename,
    original_content_type=req.content_type,
    byte_size=req.size_bytes,
    status=MediaStatus.UPLOAD_PENDING.value,
    )

    db.add(media)
    db.flush()

    storage_key = StorageService.generate_raw_key(
        tenant_ctx.tenant_id,
        meeting.id,
        media.id,
        ext,
    )

    media.storage_key = storage_key
    
    upload_id = storage.initialize_multipart_upload(
    "knowra-raw",
    storage_key,
    req.content_type,
    )

    part_size = math.ceil(req.size_bytes / req.parts_count)

    if part_size < 5 * 1024 * 1024 and req.parts_count > 1:
        raise HTTPException(
            status_code=400,
            detail="Part size must be > 5MB",
        )

    session = UploadSession(
        tenant_id=tenant_ctx.tenant_id,
        media_asset_id=media.id,
        provider_upload_id=upload_id,
        parts_count=req.parts_count,
        part_size_bytes=part_size,
        is_completed=False,
        is_aborted=False,
    )

    db.add(session)
    db.commit()

    parts = []
    for i in range(1, req.parts_count + 1):
        url = storage.generate_presigned_part_url("knowra-raw", storage_key, upload_id, i, timedelta(hours=1))
        parts.append(PartUrl(part_number=i, upload_url=url))

    return MediaUploadResponse(media_id=media.id, upload_id=upload_id, parts=parts)

@router.post("/media/{media_id}/complete", response_model=MediaStatusResponse)
def complete_media_upload(
    media_id: UUID,
    req: MediaCompleteRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    storage: ObjectStorage = Depends(get_storage_client)
):
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id, MediaAsset.tenant_id == tenant_ctx.tenant_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    upload_session = (
        db.query(UploadSession)
        .filter(
            UploadSession.media_asset_id == media.id,
            UploadSession.provider_upload_id == req.upload_id,
            UploadSession.tenant_id == tenant_ctx.tenant_id,
        )
        .first()
    )
    if not upload_session:
        raise HTTPException(status_code=404, detail="Upload session not found")

    if upload_session.is_completed:
        return media # Idempotent return

    parts_dict = [{"part_number": str(p.part_number), "etag": p.etag} for p in req.parts]
    success = storage.complete_multipart_upload("knowra-raw", media.storage_key, req.upload_id, parts_dict)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to complete multipart upload with storage provider")

    # Verify exact size
    head = storage.head_object("knowra-raw", media.storage_key)
    if head:
        media.byte_size = head["size"]

    upload_session.is_completed = True
    media.status = MediaStatus.UPLOADED.value
    db.commit()

    # Dispatch celery task
    trigger_media_pipeline(str(tenant_ctx.tenant_id), str(media.id))

    return media
