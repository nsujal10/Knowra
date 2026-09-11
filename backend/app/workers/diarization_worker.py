import os
import shutil
import tempfile
import structlog
from datetime import datetime, timezone
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.enums import ArtifactType
from app.models.processing_job import ProcessingJob
from app.ai.diarization.factory import get_diarization_provider
from app.ai.diarization.schemas import DiarizationOptions
from app.services.diarization_service import DiarizationService
from app.storage.minio import get_storage_client

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def execute_diarization_task(self, job_id: str, tenant_id: str, media_id: str):
    log = logger.bind(job_id=job_id, tenant_id=tenant_id, media_id=media_id)
    log.info("Starting Enterprise Speaker Diarization Job")

    db = SessionLocal()
    storage = get_storage_client()
    workspace_dir = os.path.join(tempfile.gettempdir(), "knowra", f"diarization_{job_id}")

    try:
        # 1. Validate Tenant Isolation & Fetch Job / Media
        media = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id == UUID(media_id),
                MediaAsset.tenant_id == UUID(tenant_id),
            )
            .first()
        )
        job = (
            db.query(ProcessingJob)
            .filter(
                ProcessingJob.id == UUID(job_id),
                ProcessingJob.tenant_id == UUID(tenant_id),
            )
            .first()
        )

        if not media or not job or str(media.tenant_id) != tenant_id:
            raise ValueError("Tenant isolation breach or missing entities.")

        job.status = "PROCESSING"
        db.commit()

        # 2. Locate Phase 10 Normalized Audio Artifact
        artifact = (
            db.query(MediaArtifact)
            .filter(
                MediaArtifact.media_asset_id == UUID(media_id),
                MediaArtifact.artifact_type == ArtifactType.NORMALIZED_AUDIO,
                MediaArtifact.tenant_id == UUID(tenant_id),
            )
            .first()
        )

        if not artifact:
            raise ValueError("Canonical NORMALIZED_AUDIO artifact not found for diarization.")

        # 3. Download Audio to Secure Workspace
        os.makedirs(workspace_dir, exist_ok=True)
        local_audio_path = os.path.join(workspace_dir, "audio.wav")
        download_success = storage.download_file(
            "knowra-derived",
            artifact.storage_key,
            local_audio_path,
        )
        if not download_success or not os.path.exists(local_audio_path):
            raise RuntimeError(f"Failed to download audio artifact: {artifact.storage_key}")

        # 4. Execute Diarization via Provider Abstraction
        provider = get_diarization_provider()
        options = DiarizationOptions()
        result = provider.diarize(local_audio_path, options)

        # 5. Persist Results, Align with Transcript, & Upload MinIO Artifact
        service = DiarizationService(db, UUID(tenant_id))
        service.save_diarization(
            meeting_id=media.meeting_id,
            media_id=UUID(media_id),
            result=result,
            job_id=UUID(job_id),
        )

        # 6. Mark Job Completed
        job.status = "COMPLETED"
        job.metadata_json = {
            "speakers_count": len(result.speakers),
            "segments_count": len(result.segments),
            "model_name": result.model_name,
        }
        db.commit()

        log.info(
            "Diarization job completed successfully",
            speakers_count=len(result.speakers),
            segments_count=len(result.segments),
        )

    except Exception as e:
        log.exception("Diarization task failed", error=str(e))
        job = db.query(ProcessingJob).filter(ProcessingJob.id == UUID(job_id)).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            db.commit()
        raise self.retry(exc=e, countdown=30)
    finally:
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        db.close()
