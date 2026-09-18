"""
Legacy stub task definitions. Production pipeline lives in:
  - app.workers.media_pipeline
  - app.workers.transcription_worker
  - app.workers.diarization_worker

These stubs must never write shared paths like /tmp/audio.wav.
"""

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.meeting_repository import MeetingRepository
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def validate_media_task(self, media_uri: str):
    logger.info("Validating media", uri=media_uri)
    return {"status": "validated", "uri": media_uri}


@celery_app.task(bind=True)
def normalize_audio_task(self, data: dict):
    """Stub — use workers.media_pipeline.normalize_audio_task in production."""
    meeting_id = data.get("meeting_id")
    media_id = data.get("media_id")
    logger.info("Stub normalize_audio_task", meeting_id=meeting_id, media_id=media_id)
    return {
        "status": "normalized",
        "meeting_id": meeting_id,
        "media_id": media_id,
        "audio_path": data.get("audio_path"),
    }


@celery_app.task(bind=True)
def transcribe_task(self, data: dict):
    """Stub — use workers.transcription_worker.execute_transcription_task."""
    meeting_id = data.get("meeting_id")
    media_id = data.get("media_id")
    logger.info("Stub transcribe_task", meeting_id=meeting_id, media_id=media_id)
    return {"status": "transcribed", "meeting_id": meeting_id, "media_id": media_id}


@celery_app.task(bind=True)
def diarize_task(self, data: dict):
    """Stub — use workers.diarization_worker.execute_diarization_task."""
    meeting_id = data.get("meeting_id")
    media_id = data.get("media_id")
    logger.info("Stub diarize_task", meeting_id=meeting_id, media_id=media_id)
    return {"status": "diarized", "meeting_id": meeting_id, "media_id": media_id}


@celery_app.task(bind=True)
def extract_intelligence_task(self, data: dict):
    """Delegates to isolated production extraction task in app.workers.intelligence_tasks."""
    from app.workers.intelligence_tasks import extract_intelligence_task as prod_task
    tenant_id = data.get("tenant_id")
    meeting_id = data.get("meeting_id")
    transcript_version = data.get("transcript_version")
    force = data.get("force", False)
    if not tenant_id or not meeting_id:
        logger.error("Missing tenant_id or meeting_id in extract_intelligence_task payload", data=data)
        return {"status": "FAILED", "reason": "Missing tenant_id or meeting_id"}
    return prod_task(tenant_id=str(tenant_id), meeting_id=str(meeting_id), transcript_version=transcript_version, force=force)


@celery_app.task(bind=True)
def index_embeddings_task(self, data: dict):
    meeting_id = data.get("meeting_id")
    logger.info("Stub index_embeddings_task", meeting_id=meeting_id)
    return {"status": "indexed", "meeting_id": meeting_id}


@celery_app.task(bind=True)
def process_meeting_task(self, tenant_id: str, meeting_id: str):
    log = logger.bind(tenant_id=tenant_id, meeting_id=meeting_id, job_id=self.request.id)

    db = SessionLocal()
    try:
        repo = MeetingRepository(db, UUID(tenant_id))
        meeting = repo.get_by_id(UUID(meeting_id))

        if not meeting:
            log.error("Tenant isolation check failed in worker: Meeting not found or access denied")
            raise ValueError("Meeting access denied or not found for tenant")

        log.info("Tenant isolation passed. Processing meeting...")
        return {"status": "success", "meeting": str(meeting.id)}
    finally:
        db.close()
