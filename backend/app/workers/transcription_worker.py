from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.enums import ArtifactType
from app.models.transcription_run import TranscriptionRun
from app.models.processing_job import ProcessingJob
from app.ai.transcription.factory import get_transcription_provider
from app.ai.transcription.schemas import TranscriptionOptions
from app.services.transcription_service import TranscriptionService
from app.storage.minio import get_storage_client
from datetime import datetime, timezone
from uuid import UUID
import structlog
import os
import tempfile
import time

logger = structlog.get_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def execute_transcription_task(self, job_id: str, tenant_id: str, media_id: str):
    log = logger.bind(job_id=job_id, tenant_id=tenant_id, media_id=media_id)
    log.info("Starting Enterprise Transcription Job")
    
    db = SessionLocal()
    storage = get_storage_client()
    workspace_dir = os.path.join(tempfile.gettempdir(), "knowra", f"transcription_{job_id}")
    start_time = time.time()
    
    try:
        # Validate Tenant Isolation & Idempotency
        media = db.query(MediaAsset).filter(
            MediaAsset.id == UUID(media_id),
            MediaAsset.tenant_id == UUID(tenant_id),
        ).first()
        job = db.query(ProcessingJob).filter(
            ProcessingJob.id == UUID(job_id),
            ProcessingJob.tenant_id == UUID(tenant_id),
        ).first()
        
        if not media or not job or str(media.tenant_id) != tenant_id:
            raise ValueError("Tenant isolation breach or missing entities.")
            
        # Ensure we haven't already completed this run (idempotency check)
        existing_run = db.query(TranscriptionRun).filter(
            TranscriptionRun.media_asset_id == UUID(media_id),
            TranscriptionRun.status == "COMPLETED"
        ).first()
        if existing_run:
            log.info("Transcription already completed for this media. Skipping.")
            return

        # Initialize run
        run = TranscriptionRun(
            tenant_id=UUID(tenant_id),
            media_asset_id=UUID(media_id),
            job_id=UUID(job_id),
            status="IN_PROGRESS"
        )
        db.add(run)
        job.status = "PROCESSING"
        db.commit()
        
        # Locate Phase 10 Artifact (NORMALIZED_AUDIO)
        artifact = db.query(MediaArtifact).filter(
            MediaArtifact.media_asset_id == UUID(media_id),
            MediaArtifact.artifact_type == ArtifactType.NORMALIZED_AUDIO,
            MediaArtifact.tenant_id == UUID(tenant_id)
        ).first()
        
        if not artifact:
            raise ValueError("Canonical NORMALIZED_AUDIO artifact not found.")

        # Download Audio
        os.makedirs(workspace_dir, exist_ok=True)
        local_audio_path = os.path.join(workspace_dir, "audio.wav")
        download_success = storage.download_file(
            "knowra-derived",
            artifact.storage_key,
            local_audio_path,
        )
        if not download_success or not os.path.exists(local_audio_path):
            raise RuntimeError(f"Failed to download audio artifact: {artifact.storage_key}")
        
        # Execute Transcription via Provider Abstraction
        provider = get_transcription_provider()
        options = TranscriptionOptions(word_timestamps=True, beam_size=5)
        result = provider.transcribe(local_audio_path, options)
        
        # Save to DB & MinIO
        svc = TranscriptionService(db, UUID(tenant_id))
        svc.save_transcription(media.meeting_id, UUID(media_id), result)
        
        # Calculate RTF (Real-Time Factor)
        processing_time = time.time() - start_time
        rtf = processing_time / result.duration if result.duration > 0 else 0
        
        # Mark Success
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)
        run.rtf = rtf
        job.status = "COMPLETED"
        job.metadata_json = {"rtf": rtf, "duration_seconds": result.duration}
        db.commit()
        
        log.info("Transcription completed successfully", rtf=rtf)
        
    except Exception as e:
        log.exception("Transcription task failed")
        job = db.query(ProcessingJob).filter(ProcessingJob.id == UUID(job_id)).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
        run = db.query(TranscriptionRun).filter(TranscriptionRun.job_id == UUID(job_id)).first()
        if run:
            run.status = "FAILED"
            run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise self.retry(exc=e, countdown=30)
    finally:
        import shutil
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir)
        db.close()
