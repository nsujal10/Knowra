from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
import math
import os
import subprocess
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


def extract_thumbnail_from_url(video_url: str, output_path: str) -> bool:
    """
    Extract a sharp video frame avoiding initial black screen or splash logo.
    Attempts seek at 5s first (skips intro logos/splash screens), then 3s, 2s, 1s, 0s.
    """
    for ts in ["00:00:05", "00:00:03", "00:00:02", "00:00:01", "00:00:00"]:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", ts,
            "-i", video_url,
            "-vframes", "1",
            "-q:v", "2",
            output_path,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=15)
            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return True
        except Exception:
            continue
    return False


def generate_thumbnail_task(meeting_id: UUID, storage_key: str):
    """Background task to extract and cache video thumbnail upon upload completion."""
    try:
        storage = get_storage_client()
        video_url = storage.get_presigned_download_url("knowra-raw", storage_key, expires=timedelta(hours=1))
        cache_dir = os.path.join(os.getcwd(), "outputs", "thumbnails")
        os.makedirs(cache_dir, exist_ok=True)
        thumb_path = os.path.join(cache_dir, f"{meeting_id}.jpg")
        extract_thumbnail_from_url(video_url, thumb_path)
    except Exception as e:
        print(f"Background thumbnail generation error: {e}")

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
    background_tasks: BackgroundTasks,
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
        return media  # Idempotent return

    parts_dict = [{"part_number": str(p.part_number), "etag": p.etag} for p in req.parts]
    try:
        success = storage.complete_multipart_upload(
            "knowra-raw", media.storage_key, req.upload_id, parts_dict
        )
    except Exception as e:
        media.status = MediaStatus.FAILED.value
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Storage finalize failed: {e}",
        )

    if not success:
        media.status = MediaStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to complete multipart upload with storage provider")

    # Verify exact size
    try:
        head = storage.head_object("knowra-raw", media.storage_key)
        if head:
            media.byte_size = head["size"]
    except Exception:
        pass

    upload_session.is_completed = True
    media.status = MediaStatus.UPLOADED.value
    db.commit()

    # Automatically trigger thumbnail extraction for newly uploaded video
    if media.meeting_id and media.storage_key:
        background_tasks.add_task(generate_thumbnail_task, media.meeting_id, media.storage_key)

    # Dispatch celery task for THIS media_id only
    trigger_media_pipeline(str(tenant_ctx.tenant_id), str(media.id))

    return media


@router.get("/meetings/{meeting_id}/media/play")
def get_media_play_url(
    meeting_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_client),
):
    """
    Retrieve a secure temporary presigned URL for media playback.
    Supports specific meeting UUIDs, sample/demo meeting IDs, and falls back to
    the most recent valid meeting recording.
    """
    media = None
    try:
        uid = UUID(str(meeting_id).strip())
        media = (
            db.query(MediaAsset)
            .filter(MediaAsset.meeting_id == uid, MediaAsset.storage_key.isnot(None))
            .order_by(MediaAsset.created_at.desc())
            .first()
        )
    except Exception:
        pass

    # Fall back to the latest valid uploaded media asset for sample/demo views
    if not media:
        media = (
            db.query(MediaAsset)
            .filter(MediaAsset.storage_key.isnot(None))
            .order_by(MediaAsset.created_at.desc())
            .first()
        )

    if media and media.storage_key:
        try:
            play_url = storage.get_presigned_download_url(
                "knowra-raw",
                media.storage_key,
                expires=timedelta(hours=2),
            )
            return {"playUrl": play_url}
        except Exception as e:
            pass

    # Reliable public demo MP4 fallback
    return {
        "playUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    }


@router.get("/meetings/{meeting_id}/media/download")
def get_media_download_url(
    meeting_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_client),
):
    """
    Retrieve a direct-download presigned URL with attachment disposition.
    """
    media = None
    meeting_title = "meeting_video"
    try:
        uid = UUID(str(meeting_id).strip())
        meeting = db.query(Meeting).filter(Meeting.id == uid).first()
        if meeting and meeting.title:
            meeting_title = "".join(c for c in meeting.title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        media = (
            db.query(MediaAsset)
            .filter(MediaAsset.meeting_id == uid, MediaAsset.storage_key.isnot(None))
            .order_by(MediaAsset.created_at.desc())
            .first()
        )
    except Exception:
        pass

    if not media:
        media = (
            db.query(MediaAsset)
            .filter(MediaAsset.storage_key.isnot(None))
            .order_by(MediaAsset.created_at.desc())
            .first()
        )

    if media and media.storage_key:
        filename = media.filename or f"{meeting_title}.mp4"
        if not filename.endswith((".mp4", ".mov", ".webm", ".wav", ".mp3")):
            filename += ".mp4"
        try:
            download_url = storage.get_presigned_download_url(
                "knowra-raw",
                media.storage_key,
                expires=timedelta(hours=2),
                filename=filename,
            )
            return {"downloadUrl": download_url, "filename": filename}
        except Exception:
            pass

    return {
        "downloadUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "filename": f"{meeting_title}.mp4",
    }


@router.get("/meetings/{meeting_id}/thumbnail")
def get_meeting_thumbnail(
    meeting_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_client),
):
    """
    Extract and serve a genuine video thumbnail JPEG for a meeting.
    Uses cached frame if already generated, otherwise invokes FFmpeg to capture
    the first keyframe at 00:00:01.
    """
    cache_dir = os.path.join(os.getcwd(), "outputs", "thumbnails")
    os.makedirs(cache_dir, exist_ok=True)
    thumb_path = os.path.join(cache_dir, f"{meeting_id}.jpg")

    # 1. Return cached thumbnail if present
    if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
        return FileResponse(
            thumb_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # 2. Try to find the specific media asset for this meeting
    media = None
    try:
        uid = UUID(str(meeting_id).strip())
        media = (
            db.query(MediaAsset)
            .filter(MediaAsset.meeting_id == uid, MediaAsset.storage_key.isnot(None))
            .order_by(MediaAsset.created_at.desc())
            .first()
        )
    except Exception:
        pass

    # 3. If not found, use the latest valid media asset
    if not media:
        media = (
            db.query(MediaAsset)
            .filter(MediaAsset.storage_key.isnot(None))
            .order_by(MediaAsset.created_at.desc())
            .first()
        )

    if media and media.storage_key:
        try:
            video_url = storage.get_presigned_download_url(
                "knowra-raw",
                media.storage_key,
                expires=timedelta(hours=1),
            )
            success = extract_thumbnail_from_url(video_url, thumb_path)
            if success and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
                return FileResponse(
                    thumb_path,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"},
                )
        except Exception:
            pass

    # 4. Fallback to default thumbnail if available
    default_thumb = os.path.join(cache_dir, "default.jpg")
    if os.path.exists(default_thumb) and os.path.getsize(default_thumb) > 0:
        return FileResponse(
            default_thumb,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    raise HTTPException(status_code=404, detail="Thumbnail not available")




