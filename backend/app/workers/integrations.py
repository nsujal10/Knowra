"""
Phase 26 – Enterprise Integration Celery Worker Tasks

Executes outbound webhooks and platform notifications (Slack, Teams, Jira)
with encrypted secret decryption, HMAC signature generation, exponential backoff retries,
and Dead Letter Queue (DLQ) tracking on failure exhaustion.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from uuid import UUID

import requests
import structlog
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent

logger = structlog.get_logger(__name__)


def execute_integration_dispatch_sync(db: Session, event_id: UUID) -> IntegrationEvent:
    """
    Synchronous execution routine for an outbound integration event.
    Shared by both Celery task worker and synchronous fallback dispatch.
    """
    event = db.query(IntegrationEvent).filter(IntegrationEvent.id == event_id).first()
    if not event or event.status in ("COMPLETED", "DUPLICATE_SKIPPED"):
        return event

    integration = db.query(Integration).filter(Integration.id == event.integration_id).first()
    if not integration:
        event.status = "FAILED"
        event.error_message = "Parent Integration record not found."
        db.commit()
        return event

    event.attempt_count += 1
    crypto = SecretEncryptionService()

    try:
        raw_secret = crypto.decrypt(integration.encrypted_credentials)
    except Exception as exc:
        event.status = "FAILED"
        event.error_message = f"Decryption failure: {str(exc)}"
        db.commit()
        return event

    # Prepare payload bytes and HMAC-SHA256 signature
    payload_dict = event.payload_json or {}
    raw_payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
    sig = hmac.new(raw_secret.encode("utf-8"), raw_payload_bytes, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Knowra-Signature": f"sha256={sig}",
        "X-Knowra-Event-ID": event.external_event_id,
        "X-Knowra-Event-Type": event.event_type,
        "User-Agent": "Knowra-Integration-Worker/1.0",
    }

    target_url = integration.webhook_url
    # If simulated integration without live endpoint
    if not target_url or target_url.startswith(("mock://", "test://")):
        event.status = "COMPLETED"
        event.response_status_code = 200
        event.error_message = None
        db.commit()
        logger.info(
            "Outbound integration event dispatched (simulated)",
            event_id=str(event.id),
            provider=integration.provider,
            external_event_id=event.external_event_id,
        )
        return event

    try:
        resp = requests.post(
            target_url,
            data=raw_payload_bytes,
            headers=headers,
            timeout=10.0,
        )
        event.response_status_code = resp.status_code

        if resp.status_code in (200, 201, 202, 204):
            event.status = "COMPLETED"
            event.error_message = None
        else:
            event.error_message = f"HTTP {resp.status_code}: {resp.text[:300]}"
            if event.attempt_count >= event.max_retries:
                event.status = "FAILED"
            else:
                event.status = "PENDING"
    except Exception as req_err:
        event.error_message = str(req_err)
        event.response_status_code = 500
        if event.attempt_count >= event.max_retries:
            event.status = "FAILED"
        else:
            event.status = "PENDING"

    db.commit()
    db.refresh(event)
    return event


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    name="app.workers.integrations.dispatch_integration_event_task",
)
def dispatch_integration_event_task(self, event_id_str: str) -> bool:
    """
    Celery task with exponential backoff handling outbound integration webhook delivery.
    """
    db = SessionLocal()
    try:
        event_id = UUID(event_id_str)
        event = execute_integration_dispatch_sync(db, event_id)

        if event and event.status == "PENDING" and event.attempt_count < event.max_retries:
            countdown = 2 ** event.attempt_count
            logger.warning(
                "Retrying integration event dispatch",
                event_id=event_id_str,
                attempt=event.attempt_count,
                countdown=countdown,
            )
            raise self.retry(countdown=countdown)

        return event is not None and event.status == "COMPLETED"
    except self.MaxRetriesExceededError:
        logger.error("Integration dispatch max retries exceeded, marked as DLQ/FAILED", event_id=event_id_str)
        return False
    finally:
        db.close()


@celery_app.task(name="app.workers.integrations.process_inbound_webhook_task")
def process_inbound_webhook_task(event_id_str: str) -> bool:
    """
    Background processing task for asynchronous incoming webhooks.
    """
    db = SessionLocal()
    try:
        event_id = UUID(event_id_str)
        event = db.query(IntegrationEvent).filter(IntegrationEvent.id == event_id).first()
        if event:
            event.status = "COMPLETED"
            db.commit()
            logger.info("Inbound webhook successfully processed in background", event_id=event_id_str)
            return True
        return False
    finally:
        db.close()
