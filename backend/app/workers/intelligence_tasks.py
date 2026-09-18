from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.intelligence.extraction.service import (
    MeetingIntelligenceService,
    InsufficientTranscriptError,
    IntelligenceNotFoundError,
)
from app.models.meeting import Meeting

logger = structlog.get_logger(__name__)


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Provide a transactional DB session isolated to a single Celery task execution."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def extract_intelligence_task(
    self,
    tenant_id: str,
    meeting_id: str,
    transcript_version: Optional[int] = None,
    force: bool = False,
) -> dict:
    """
    Celery task for meeting intelligence extraction.
    Guarantees absolute task isolation, strict MinIO pathing, and deterministic validation.
    """
    log = logger.bind(
        celery_task_id=self.request.id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        attempt=self.request.retries,
    )
    log.info("Starting isolated intelligence extraction task")

    tenant_uuid = UUID(str(tenant_id).strip())
    meeting_uuid = UUID(str(meeting_id).strip())

    with get_db_context() as db:
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id == meeting_uuid, Meeting.tenant_id == tenant_uuid)
            .first()
        )
        if not meeting:
            log.error("Meeting not found or tenant isolation check failed")
            return {"status": "FAILED", "reason": "Meeting not found"}

        service = MeetingIntelligenceService(db=db, tenant_id=tenant_uuid)

        try:
            res = service.run_intelligence(
                meeting_id=meeting_uuid,
                transcript_version_number=transcript_version,
                force=force,
            )
            # Update meeting status to COMPLETED
            meeting.status = "COMPLETED"
            db.commit()

            log.info("Intelligence extraction task completed successfully", run_id=str(res.run_id))
            return {
                "status": "COMPLETED",
                "meeting_id": meeting_id,
                "run_id": str(res.run_id),
                "topics_count": len(res.topics),
                "decisions_count": len(res.decisions),
            }

        except InsufficientTranscriptError as e:
            log.warning("Intelligence task aborted due to insufficient transcript", error=str(e))
            meeting.status = "FAILED_NO_TRANSCRIPT"
            db.commit()
            return {"status": "FAILED_NO_TRANSCRIPT", "reason": str(e)}

        except IntelligenceNotFoundError as e:
            log.error("Transcript or meeting not found for intelligence extraction", error=str(e))
            meeting.status = "FAILED"
            db.commit()
            return {"status": "FAILED", "reason": str(e)}

        except Exception as exc:
            log.exception("Intelligence extraction task failed", error=str(exc))
            meeting.status = "FAILED"
            db.commit()

            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)
            return {"status": "FAILED", "reason": str(exc)}
