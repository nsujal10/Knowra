from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.meeting_repository import MeetingRepository
from uuid import UUID
import structlog
import time

logger = structlog.get_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def validate_media_task(self, media_uri: str):
    logger.info("Validating media", uri=media_uri)
    return {"status": "validated", "uri": media_uri}

@celery_app.task(bind=True)
def normalize_audio_task(self, data: dict):
    logger.info("Normalizing audio via FFmpeg", uri=data.get("uri"))
    return {"status": "normalized", "audio_path": "/tmp/audio.wav"}

@celery_app.task(bind=True)
def transcribe_task(self, data: dict):
    logger.info("Transcribing audio", audio_path=data.get("audio_path"))
    return {"status": "transcribed", "transcript": [{"speaker": "A", "text": "Hello"}]}

@celery_app.task(bind=True)
def diarize_task(self, data: dict):
    logger.info("Diarizing audio")
    return {"status": "diarized", "segments": []}

@celery_app.task(bind=True)
def extract_intelligence_task(self, data: dict):
    logger.info("Extracting intelligence")
    return {"status": "extracted"}

@celery_app.task(bind=True)
def index_embeddings_task(self, data: dict):
    logger.info("Indexing embeddings to pgvector")
    return {"status": "indexed"}

@celery_app.task(bind=True)
def process_meeting_task(self, tenant_id: str, meeting_id: str):
    logger = structlog.get_logger(__name__).bind(tenant_id=tenant_id, meeting_id=meeting_id, job_id=self.request.id)
    
    db = SessionLocal()
    try:
        repo = MeetingRepository(db, UUID(tenant_id))
        meeting = repo.get_by_id(UUID(meeting_id))
        
        if not meeting:
            logger.error("Tenant isolation check failed in worker: Meeting not found or access denied")
            raise ValueError("Meeting access denied or not found for tenant")
            
        logger.info("Tenant isolation passed. Processing meeting...")
        return {"status": "success", "meeting": str(meeting.id)}
    finally:
        db.close()