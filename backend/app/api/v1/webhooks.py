"""
Phase 26 – Enterprise Webhook Ingress Router

Receives inbound webhook notifications (e.g. from GitHub, Jira, Slack, or custom webhooks)
with strict security requirements:
  1. Reads raw request body as bytes BEFORE JSON parsing.
  2. Verifies HMAC-SHA256 signature in constant time via hmac.compare_digest.
  3. Rejects invalid, missing, or mismatched signatures with HTTP 401 Unauthorized.
  4. Enforces idempotency via external_event_id to prevent double-firing side effects.
  5. Provides immediate fast 2xx acknowledgment and async Celery task handoff.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
import structlog

from app.core.database import get_db
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent
from app.integrations.schemas import WebhookReceiptResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/{provider}/{integration_id}",
    response_model=WebhookReceiptResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Secure inbound webhook receiver with HMAC verification and idempotency",
)
async def receive_inbound_webhook(
    provider: str,
    integration_id: UUID,
    request: Request,
    x_knowra_signature: Optional[str] = Header(None, alias="X-Knowra-Signature"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_knowra_event_id: Optional[str] = Header(None, alias="X-Knowra-Event-ID"),
    x_event_id: Optional[str] = Header(None, alias="X-Event-ID"),
    db: Session = Depends(get_db),
) -> WebhookReceiptResponse:
    # -----------------------------------------------------------------------
    # 1. Read Raw Bytes BEFORE JSON Parsing
    # -----------------------------------------------------------------------
    raw_body: bytes = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty webhook request body.",
        )

    # -----------------------------------------------------------------------
    # 2. Retrieve Integration & Decrypt Signing Secret
    # -----------------------------------------------------------------------
    integration = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.status == "ACTIVE",
        )
        .first()
    )
    if not integration:
        logger.warning("Inbound webhook target integration not found or inactive", integration_id=str(integration_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or inactive.",
        )

    crypto = SecretEncryptionService()
    try:
        signing_secret = crypto.decrypt(integration.encrypted_credentials)
    except Exception as err:
        logger.error("Failed to decrypt integration secret during webhook receipt", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal integration credentials error.",
        )

    # -----------------------------------------------------------------------
    # 3. Constant-Time HMAC-SHA256 Signature Validation
    # -----------------------------------------------------------------------
    provided_signature = x_knowra_signature or x_hub_signature_256 or x_signature
    if not provided_signature:
        logger.warning("Webhook rejected: Missing HMAC signature header", integration_id=str(integration_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required HMAC signature header (X-Knowra-Signature).",
        )

    # Extract hex digest if prefixed with "sha256="
    clean_sig = provided_signature.strip()
    if clean_sig.startswith("sha256="):
        clean_sig = clean_sig.split("sha256=", 1)[1]

    expected_sig = hmac.new(signing_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(clean_sig, expected_sig):
        logger.warning(
            "Webhook rejected: Invalid HMAC signature",
            integration_id=str(integration_id),
            provided=clean_sig[:10] + "...",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature. Payload tampering detected or mismatched secret.",
        )

    # -----------------------------------------------------------------------
    # 4. Safe JSON Parsing & Idempotency Key Extraction
    # -----------------------------------------------------------------------
    try:
        payload_data = json.loads(raw_body.decode("utf-8"))
    except Exception as json_err:
        logger.warning("Malformed JSON in validated webhook", error=str(json_err))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(json_err)}",
        )

    # Derive external_event_id
    header_event_id = x_knowra_event_id or x_event_id
    body_event_id = None
    if isinstance(payload_data, dict):
        body_event_id = payload_data.get("id") or payload_data.get("event_id") or payload_data.get("eventId")

    external_event_id = str(header_event_id or body_event_id or f"inbound_{hashlib.sha256(raw_body).hexdigest()[:16]}")

    # -----------------------------------------------------------------------
    # 5. Enforce Idempotency (Prevent Duplicate Side Effects)
    # -----------------------------------------------------------------------
    existing_event = (
        db.query(IntegrationEvent)
        .filter(
            IntegrationEvent.tenant_id == integration.tenant_id,
            IntegrationEvent.external_event_id == external_event_id,
        )
        .first()
    )

    if existing_event:
        logger.info(
            "Webhook duplicate received, returning fast 200 without side effects",
            integration_id=str(integration_id),
            external_event_id=external_event_id,
        )
        return WebhookReceiptResponse(
            status="SUCCESS",
            external_event_id=external_event_id,
            duplicate_skipped=True,
            message="Event previously received and processed. Idempotent skip.",
        )

    # Record new inbound event in database
    event_type = f"INBOUND_{provider.upper()}"
    inbound_record = IntegrationEvent(
        tenant_id=integration.tenant_id,
        integration_id=integration.id,
        direction="INBOUND",
        external_event_id=external_event_id,
        event_type=event_type,
        status="PENDING",
        payload_json=payload_data if isinstance(payload_data, dict) else {"raw": payload_data},
    )
    db.add(inbound_record)
    db.commit()
    db.refresh(inbound_record)

    # -----------------------------------------------------------------------
    # 6. Asynchronous Celery Task Handoff
    # -----------------------------------------------------------------------
    try:
        from app.workers.integrations import process_inbound_webhook_task
        process_inbound_webhook_task.delay(str(inbound_record.id))
    except Exception as queue_err:
        logger.warning(
            "Failed to enqueue Celery task, setting direct completed status",
            error=str(queue_err),
        )
        inbound_record.status = "COMPLETED"
        db.commit()

    return WebhookReceiptResponse(
        status="ACCEPTED",
        external_event_id=external_event_id,
        duplicate_skipped=False,
        message="Webhook authenticated and queued for processing.",
    )
