import hashlib
import hmac
import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration
from app.main import app
from app.models.organization import Organization

client = TestClient(app)

TEST_SECRET = "super-secret-integration-webhook-token-32b"


@pytest.fixture(scope="module")
def setup_integration():
    db = SessionLocal()
    crypto = SecretEncryptionService()
    
    # Ensure tenant exists
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="Webhook Test Org", slug=f"webhook-org-{uuid.uuid4().hex[:6]}")
        db.add(org)
        db.commit()
        db.refresh(org)

    # Create active integration with encrypted secret
    encrypted_secret = crypto.encrypt(TEST_SECRET)
    integration = Integration(
        tenant_id=org.id,
        name="Security Test Webhook",
        provider="custom",
        webhook_url="https://example.com/webhook",
        status="ACTIVE",
        encrypted_credentials=encrypted_secret,
        events_subscribed=["*"],
    )
    db.add(integration)

    db.commit()
    db.refresh(integration)
    
    integration_id = integration.id
    db.close()
    
    return integration_id


def test_webhook_missing_signature(setup_integration):
    """Missing HMAC signature header returns 401 Unauthorized."""
    integration_id = setup_integration
    payload = {"event": "meeting.completed", "id": "evt-123"}
    response = client.post(
        f"/api/v1/webhooks/custom/{integration_id}",
        json=payload,
    )
    assert response.status_code == 401
    assert "Missing required HMAC signature header" in response.json()["detail"]


def test_webhook_invalid_signature(setup_integration):
    """Invalid HMAC signature returns 401 Unauthorized."""
    integration_id = setup_integration
    payload = {"event": "meeting.completed", "id": "evt-123"}
    body_bytes = json.dumps(payload).encode("utf-8")

    response = client.post(
        f"/api/v1/webhooks/custom/{integration_id}",
        content=body_bytes,
        headers={
            "X-Knowra-Signature": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401
    assert "Invalid HMAC signature" in response.json()["detail"]


def test_webhook_valid_signature_and_idempotency(setup_integration):
    """Valid HMAC signature returns 202 Accepted, and duplicate submission is skipped."""
    integration_id = setup_integration
    event_id = f"evt-secure-{uuid.uuid4().hex[:8]}"
    payload = {
        "event_id": event_id,
        "action": "task.created",
        "title": "Follow up on architecture decisions",
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(TEST_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    # 1. First request -> 202 Accepted
    response = client.post(
        f"/api/v1/webhooks/custom/{integration_id}",
        content=body_bytes,
        headers={
            "X-Knowra-Signature": f"sha256={sig}",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["duplicate_skipped"] is False
    assert data["external_event_id"] == event_id

    # 2. Duplicate submission with identical body -> duplicate_skipped is True
    dup_response = client.post(
        f"/api/v1/webhooks/custom/{integration_id}",
        content=body_bytes,
        headers={
            "X-Knowra-Signature": f"sha256={sig}",
            "Content-Type": "application/json",
        },
    )
    assert dup_response.status_code in (200, 202)
    dup_data = dup_response.json()
    assert dup_data["duplicate_skipped"] is True
    assert dup_data["external_event_id"] == event_id
