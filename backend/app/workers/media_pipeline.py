from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.enums import MediaStatus, ArtifactType
from app.storage.minio import get_storage_client
from app.storage.service import StorageService
from app.media.scanner import get_scanner
from app.media.validation import validate_file_signature
from app.media.metadata import extract_metadata
from app.media.normalization import normalize_to_wav
import structlog
import tempfile
import os

logger = structlog.get_logger(__name__)

def update_status(db, media_id, status: MediaStatus):
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if media:
        media.status = status.value
        db.commit()

@celery_app.task(bind=True, max_retries=3)
def scan_media_task(self, tenant_id: str, media_id: str):
    logger.info("Starting scan_media_task", media_id=media_id)
    db = SessionLocal()
    storage = get_storage_client()
    try:
        media = db.query(MediaAsset).filter(MediaAsset.id == media_id, MediaAsset.tenant_id == tenant_id).first()
        if not media or media.status != MediaStatus.UPLOADED.value:
            return
            
        update_status(db, media.id, MediaStatus.SCANNING)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "source")
            storage.download_file("knowra-raw", media.storage_key, local_path)
            
            # 1. Magic Bytes Validation
            actual_mime = validate_file_signature(local_path)
            if not actual_mime:
                update_status(db, media.id, MediaStatus.FAILED)
                raise ValueError("Invalid magic bytes signature")
                
            # 2. Virus Scan
            scanner = get_scanner()
            if not scanner.scan_file(local_path):
                storage.move_object("knowra-raw", media.storage_key, "knowra-quarantine", media.storage_key)
                update_status(db, media.id, MediaStatus.QUARANTINED)
                raise ValueError("Virus scan failed. Object quarantined.")

        update_status(db, media.id, MediaStatus.VALIDATED)
        # Chain next
        extract_metadata_task.delay(tenant_id, media_id)
    except Exception as e:
        logger.error("Scan failed", error=str(e))
        raise self.retry(exc=e, countdown=10)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def extract_metadata_task(self, tenant_id: str, media_id: str):
    logger.info("Starting extract_metadata_task", media_id=media_id)
    db = SessionLocal()
    storage = get_storage_client()
    try:
        media = db.query(MediaAsset).filter(MediaAsset.id == media_id, MediaAsset.tenant_id == tenant_id).first()
        if not media or media.status != MediaStatus.VALIDATED.value:
            return
            
        update_status(db, media.id, MediaStatus.METADATA_EXTRACTING)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "source")
            storage.download_file("knowra-raw", media.storage_key, local_path)
            
            meta = extract_metadata(local_path)
            if meta:
                media.duration_seconds = meta["duration"]
                media.video_codec = meta["video_codec"]
                media.audio_codec = meta["audio_codec"]
                db.commit()
                
        update_status(db, media.id, MediaStatus.PROCESSING_QUEUED)
        # Chain next
        normalize_audio_task.delay(tenant_id, media_id)
    except Exception as e:
        logger.error("Metadata extraction failed", error=str(e))
        raise self.retry(exc=e, countdown=10)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def normalize_audio_task(self, tenant_id: str, media_id: str):
    logger.info("Starting normalize_audio_task", media_id=media_id)
    db = SessionLocal()
    storage = get_storage_client()
    try:
        media = db.query(MediaAsset).filter(MediaAsset.id == media_id, MediaAsset.tenant_id == tenant_id).first()
        if not media or media.status != MediaStatus.PROCESSING_QUEUED.value:
            return
            
        update_status(db, media.id, MediaStatus.PROCESSING)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "source")
            output_path = os.path.join(tmpdir, "audio.wav")
            storage.download_file("knowra-raw", media.storage_key, input_path)
            
            success = normalize_to_wav(input_path, output_path)
            if not success:
                update_status(db, media.id, MediaStatus.FAILED)
                return

            derived_key = StorageService.generate_derived_key(media.tenant_id, media.meeting_id, media.id, "16khz_mono", "wav")
            storage.upload_file("knowra-derived", derived_key, output_path, "audio/wav")
            
            artifact = MediaArtifact(
                tenant_id=media.tenant_id,
                media_asset_id=media.id,
                artifact_type=ArtifactType.NORMALIZED_AUDIO.value,
                storage_key=derived_key,
                content_type="audio/wav",
                byte_size=os.path.getsize(output_path)
            )
            db.add(artifact)
            db.commit()

        update_status(db, media.id, MediaStatus.READY)
    except Exception as e:
        logger.error("Normalization failed", error=str(e))
        raise self.retry(exc=e, countdown=10)
    finally:
        db.close()

def trigger_media_pipeline(tenant_id: str, media_id: str):
    scan_media_task.delay(tenant_id, media_id)
