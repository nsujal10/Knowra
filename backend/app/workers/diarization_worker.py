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
from app.models.meeting import Meeting
from app.ai.diarization.factory import get_diarization_provider
from app.ai.diarization.schemas import DiarizationOptions
from app.services.diarization_service import DiarizationService
from app.storage.minio import get_storage_client

logger = structlog.get_logger(__name__)


def _trigger_intelligence(db, tenant_id: UUID, meeting_id: UUID):
    """Enqueue isolated intelligence extraction task for this meeting."""
    try:
        from app.workers.intelligence_tasks import extract_intelligence_task
        extract_intelligence_task.delay(str(tenant_id), str(meeting_id))
        logger.info("Queued isolated extract_intelligence_task after diarization", meeting_id=str(meeting_id))
    except Exception as e:
        logger.warning(
            "Could not enqueue extract_intelligence_task after diarization",
            meeting_id=str(meeting_id),
            error=str(e),
        )


@celery_app.task(bind=True, max_retries=3)
def execute_diarization_task(self, job_id: str, tenant_id: str, media_id: str):
    """
    Speaker diarization for a single (job_id, tenant_id, media_id) triple.
    All state is loaded from DB args — no module-level meeting state.
    """
    log = logger.bind(job_id=job_id, tenant_id=tenant_id, media_id=media_id)
    log.info("Starting Enterprise Speaker Diarization Job")

    db = SessionLocal()
    storage = get_storage_client()
    # Workspace isolated per job_id — never reuse a shared temp path
    workspace_dir = os.path.join(tempfile.gettempdir(), "knowra", f"diarization_{job_id}")

    try:
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

        os.makedirs(workspace_dir, exist_ok=True)
        local_audio_path = os.path.join(workspace_dir, f"audio_{media_id}.wav")
        download_success = storage.download_file(
            "knowra-derived",
            artifact.storage_key,
            local_audio_path,
        )
        if not download_success or not os.path.exists(local_audio_path):
            if os.getenv("DIARIZATION_PROVIDER") == "mock":
                with open(local_audio_path, "wb") as f:
                    f.write(
                        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                        b"D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
                    )
            else:
                raise RuntimeError(f"Failed to download audio artifact: {artifact.storage_key}")

        provider = get_diarization_provider()
        # Bound clustering to reduce over-segmentation / speaker fragmentation
        options = DiarizationOptions(min_speakers=1, max_speakers=10, merge_gap_seconds=0.5)
        result = provider.diarize(local_audio_path, options)

        service = DiarizationService(db, UUID(tenant_id))
        service.save_diarization(
            meeting_id=media.meeting_id,
            media_id=UUID(media_id),
            result=result,
            job_id=UUID(job_id),
        )

        job.status = "COMPLETED"
        job.metadata_json = {
            "speakers_count": len(result.speakers),
            "segments_count": len(result.segments),
            "model_name": result.model_name,
            "speakers": result.speakers,
        }
        db.commit()

        log.info(
            "Diarization job completed successfully",
            speakers_count=len(result.speakers),
            segments_count=len(result.segments),
        )

        # Automatically resolve real speaker identities from dialogue via Groq LLM
        try:
            from app.ai.speaker.speaker_identifier import resolve_speaker_identities
            resolve_speaker_identities(db, UUID(tenant_id), media.meeting_id)
        except Exception as spk_err:
            log.warning("AI speaker resolution encountered error", error=str(spk_err))

        # Chain intelligence for THIS meeting only
        _trigger_intelligence(db, UUID(tenant_id), media.meeting_id)

    except Exception as e:
        log.exception("Diarization task failed", error=str(e))
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == UUID(job_id)).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                db.commit()
            media = db.query(MediaAsset).filter(MediaAsset.id == UUID(media_id)).first()
            if media:
                meeting = db.query(Meeting).filter(Meeting.id == media.meeting_id).first()
                if meeting and self.request.retries >= self.max_retries:
                    meeting.status = "FAILED"
                    db.commit()
        except Exception:
            pass
        if self.request.retries >= self.max_retries:
            return
        raise self.retry(exc=e, countdown=30)
    finally:
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        db.close()
