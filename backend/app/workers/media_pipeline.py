from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.enums import MediaStatus, ArtifactType
from app.models.processing_job import ProcessingJob
from app.storage.minio import get_storage_client
from app.storage.service import StorageService
from app.media.scanner import get_scanner
from app.media.validation import validate_file_signature
from app.media.metadata import extract_metadata
from app.media.normalization import normalize_to_wav
import structlog
import tempfile
import os
from uuid import UUID
from app.models.meeting import Meeting
import hashlib

logger = structlog.get_logger(__name__)


def update_status(db, media_id, status: MediaStatus):
    """
    Update media status. Media READY means audio is normalized — meeting stays
    PROCESSING until transcription/intelligence complete (not falsely COMPLETED).
    """
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if media:
        media.status = status.value
        meeting = db.query(Meeting).filter(Meeting.id == media.meeting_id).first()
        if meeting:
            if status in [MediaStatus.FAILED, MediaStatus.QUARANTINED]:
                meeting.status = "FAILED"
            elif status == MediaStatus.READY:
                # Audio ready; ASR/intelligence still pending
                meeting.status = "PROCESSING"
            elif status in [
                MediaStatus.UPLOADED,
                MediaStatus.SCANNING,
                MediaStatus.VALIDATED,
                MediaStatus.METADATA_EXTRACTING,
                MediaStatus.PROCESSING_QUEUED,
                MediaStatus.PROCESSING,
            ]:
                meeting.status = "PROCESSING"
        db.commit()


def calculate_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def _mark_failed(db, media_id: str, error: str):
    try:
        update_status(db, media_id, MediaStatus.FAILED)
        logger.error("Media pipeline marked FAILED", media_id=media_id, error=error)
    except Exception as mark_err:
        logger.error("Failed to mark media FAILED", media_id=media_id, error=str(mark_err))


def _queue_transcription(db, tenant_id: str, media_id: str):
    """Enqueue ASR for this specific media_id — no shared/global state."""
    existing = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.media_asset_id == UUID(media_id),
            ProcessingJob.tenant_id == UUID(tenant_id),
            ProcessingJob.task_name == "TRANSCRIPTION",
            ProcessingJob.status.in_(["PENDING", "PROCESSING", "IN_PROGRESS", "COMPLETED"]),
        )
        .first()
    )
    if existing:
        logger.info("Transcription already queued/done for media", media_id=media_id, job_id=str(existing.id))
        return

    job = ProcessingJob(
        tenant_id=UUID(tenant_id),
        media_asset_id=UUID(media_id),
        task_name="TRANSCRIPTION",
        status="PENDING",
    )
    db.add(job)
    db.commit()

    from app.workers.transcription_worker import execute_transcription_task
    execute_transcription_task.delay(str(job.id), str(tenant_id), str(media_id))
    logger.info("Queued transcription after media READY", media_id=media_id, job_id=str(job.id))


@celery_app.task(bind=True, max_retries=3)
def scan_media_task(self, tenant_id: str, media_id: str):
    log = logger.bind(tenant_id=tenant_id, media_id=media_id)
    log.info("Starting scan_media_task")
    db = SessionLocal()
    storage = get_storage_client()
    try:
        media = db.query(MediaAsset).filter(
            MediaAsset.id == media_id,
            MediaAsset.tenant_id == tenant_id,
        ).first()
        if not media or media.status != MediaStatus.UPLOADED.value:
            return

        update_status(db, media.id, MediaStatus.SCANNING)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, f"source_{media_id}")
            storage.download_file("knowra-raw", media.storage_key, local_path)

            actual_mime = validate_file_signature(local_path)
            if not actual_mime:
                _mark_failed(db, media_id, "Invalid magic bytes signature")
                return

            scanner = get_scanner()
            if not scanner.scan_file(local_path):
                storage.move_object("knowra-raw", media.storage_key, "knowra-quarantine", media.storage_key)
                update_status(db, media.id, MediaStatus.QUARANTINED)
                return

        update_status(db, media.id, MediaStatus.VALIDATED)
        extract_metadata_task.delay(tenant_id, media_id)
    except Exception as e:
        log.exception("Scan failed", error=str(e))
        if self.request.retries >= self.max_retries:
            _mark_failed(db, media_id, str(e))
            return
        raise self.retry(exc=e, countdown=10)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def extract_metadata_task(self, tenant_id: str, media_id: str):
    log = logger.bind(tenant_id=tenant_id, media_id=media_id)
    log.info("Starting extract_metadata_task")
    db = SessionLocal()
    storage = get_storage_client()
    try:
        media = db.query(MediaAsset).filter(
            MediaAsset.id == media_id,
            MediaAsset.tenant_id == tenant_id,
        ).first()
        if not media or media.status != MediaStatus.VALIDATED.value:
            return

        update_status(db, media.id, MediaStatus.METADATA_EXTRACTING)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, f"source_{media_id}")
            storage.download_file("knowra-raw", media.storage_key, local_path)

            meta = extract_metadata(local_path)
            if meta:
                media.duration_seconds = meta["duration"]
                media.video_codec = meta["video_codec"]
                media.audio_codec = meta["audio_codec"]
                db.commit()

        update_status(db, media.id, MediaStatus.PROCESSING_QUEUED)
        normalize_audio_task.delay(tenant_id, media_id)
    except Exception as e:
        log.exception("Metadata extraction failed", error=str(e))
        if self.request.retries >= self.max_retries:
            _mark_failed(db, media_id, str(e))
            return
        raise self.retry(exc=e, countdown=10)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def normalize_audio_task(self, tenant_id: str, media_id: str):
    log = logger.bind(tenant_id=tenant_id, media_id=media_id)
    log.info("Starting normalize_audio_task")
    db = SessionLocal()
    storage = get_storage_client()
    try:
        media = db.query(MediaAsset).filter(
            MediaAsset.id == media_id,
            MediaAsset.tenant_id == tenant_id,
        ).first()
        if not media or media.status != MediaStatus.PROCESSING_QUEUED.value:
            return

        update_status(db, media.id, MediaStatus.PROCESSING)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, f"source_{media_id}")
            output_path = os.path.join(tmpdir, f"audio_{media_id}.wav")
            storage.download_file("knowra-raw", media.storage_key, input_path)

            success = normalize_to_wav(input_path, output_path, duration_seconds=media.duration_seconds)
            if not success:
                _mark_failed(db, media_id, "Audio normalization failed")
                return

            derived_key = StorageService.generate_derived_key(
                media.tenant_id, media.meeting_id, media.id, "16khz_mono", "wav"
            )
            storage.upload_file("knowra-derived", derived_key, output_path, "audio/wav")

            artifact = MediaArtifact(
                tenant_id=media.tenant_id,
                media_asset_id=media.id,
                artifact_type=ArtifactType.NORMALIZED_AUDIO,
                storage_key=derived_key,
                byte_size=os.path.getsize(output_path),
                checksum_sha256=calculate_sha256(output_path),
            )
            db.add(artifact)
            db.commit()

        update_status(db, media.id, MediaStatus.READY)

        # Auto-chain transcription for this meeting's media (isolated by media_id)
        _queue_transcription(db, tenant_id, media_id)
    except Exception as e:
        log.exception("Normalization failed", error=str(e))
        if self.request.retries >= self.max_retries:
            _mark_failed(db, media_id, str(e))
            return
        raise self.retry(exc=e, countdown=10)
    finally:
        db.close()


def trigger_media_pipeline(tenant_id: str, media_id: str):
    scan_media_task.delay(tenant_id, media_id)
