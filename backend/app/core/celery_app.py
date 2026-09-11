from celery import Celery
import os
import structlog

logger = structlog.get_logger(__name__)

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "enterprise_worker",
    broker=broker_url,
    backend=result_backend,
    include=[
        "app.tasks.pipeline",
        "app.workers.media_pipeline",
        "app.workers.transcription_worker",
        "app.workers.diarization_worker",
    ],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600
)

logger.info("Celery configured", broker=broker_url)
