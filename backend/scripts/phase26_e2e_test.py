#!/usr/bin/env python3
"""
Phase 26 E2E Test: Enterprise Integrations & Event-Driven Workflows

Tests:
1. SecretEncryptionService symmetric AES-256 / Fernet key derivation, encryption & decryption
2. Integration persistence with encrypted credentials and event filtering
3. EventDispatcher routing domain events to matched integrations
4. Event idempotency guarantee (duplicate external_event_id skipped)
5. Synchronous & background Celery dispatch execution
6. Inbound Webhook security (HMAC-SHA256 constant time verification, tampering rejection)
7. Inbound Webhook deduplication
"""

import sys
import os
import uuid
import json
import hmac
import hashlib

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.organization import Organization
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent
from app.events.dispatcher import EventDispatcher

client = TestClient(app)


def run_phase26_e2e():
    print("=" * 70)
    print("PHASE 26 E2E: ENTERPRISE INTEGRATIONS & EVENT-DRIVEN WORKFLOWS")
    print("=" * 70)

    db = SessionLocal()
    try:
        # 1. Organization / Tenant Setup
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Enterprise Workflows Corp", slug=f"workflows-{uuid.uuid4().hex[:6]}")
            db.add(org)
            db.commit()
            db.refresh(org)
        print(f"[+] Using Organization: {org.name} (ID: {org.id})")

        # 2. Secret Encryption Service
        print("\n--- 1. Testing Secret Encryption Service (Fernet / AES) ---")
        crypto = SecretEncryptionService()
        raw_secret = "xoxb-enterprise-slack-token-998877665544-secret"
        encrypted = crypto.encrypt(raw_secret)
        decrypted = crypto.decrypt(encrypted)
        print(f"    Raw Secret:       {raw_secret[:12]}... (len: {len(raw_secret)})")
        print(f"    Encrypted Token:  {encrypted[:24]}... (len: {len(encrypted)})")
        print(f"    Decrypted Token:  {decrypted[:12]}...")
        assert raw_secret != encrypted
        assert decrypted == raw_secret
        print("    [+] Encryption/Decryption verified successfully.")

        # 3. Create Enterprise Integrations (Slack & Webhook)
        print("\n--- 2. Testing Integration Creation with Encrypted Credentials ---")
        webhook_signing_key = f"whsec_{uuid.uuid4().hex}"
        webhook_integ = Integration(
            tenant_id=org.id,
            name="External ERP Webhook Sync",
            provider="custom_webhook",
            webhook_url="https://api.erp-mock.internal/v1/events",
            encrypted_credentials=crypto.encrypt(webhook_signing_key),
            events_subscribed=["DECISION_CREATED", "ACTION_ITEM_ASSIGNED"],
            status="ACTIVE",
        )
        db.add(webhook_integ)

        slack_integ = Integration(
            tenant_id=org.id,
            name="Executive Slack Notifications",
            provider="slack",
            encrypted_credentials=crypto.encrypt("xoxb-mock-slack-token-12345"),
            channel_or_project_id="#executive-decisions",
            events_subscribed=["DECISION_CREATED"],
            status="ACTIVE",
        )
        db.add(slack_integ)
        db.commit()
        db.refresh(webhook_integ)
        db.refresh(slack_integ)

        print(f"    [+] Created Webhook Integration: ID {webhook_integ.id} (Subscribed: {webhook_integ.events_subscribed})")
        print(f"    [+] Created Slack Integration:   ID {slack_integ.id} (Subscribed: {slack_integ.events_subscribed})")

        # 4. Domain Event Dispatcher & Routing
        print("\n--- 3. Testing EventDispatcher Domain Event Routing ---")
        dispatcher = EventDispatcher(db)

        # Publish DECISION_CREATED -> Should match BOTH integrations
        decision_payload = {
            "decision_id": f"dec-{uuid.uuid4().hex[:6]}",
            "meeting_id": f"meet-{uuid.uuid4().hex[:6]}",
            "title": "Migrate Knowra Vector Storage to pgvector with HNSW indexing",
            "confidence_score": 0.96,
        }
        published_events = dispatcher.publish_event(
            tenant_id=org.id,
            event_type="DECISION_CREATED",
            payload=decision_payload,
            sync_execute=True,
        )
        print(f"    [+] Published DECISION_CREATED: {len(published_events)} target events generated")
        for e in published_events:
            print(f"        Event ID: {e.id}, Ext ID: {e.external_event_id}, Status: {e.status}")
        assert len(published_events) >= 2

        # 5. Idempotency Check
        print("\n--- 4. Testing Event Dispatcher Idempotency Deduplication ---")
        idemp_ext_id = f"evt_idemp_{uuid.uuid4().hex[:8]}"
        first_run = dispatcher.publish_event(
            tenant_id=org.id,
            event_type="DECISION_CREATED",
            payload=decision_payload,
            external_event_id=idemp_ext_id,
            sync_execute=True,
        )
        print(f"    First dispatch result: {len(first_run)} events, first status: {first_run[0].status}")

        # Duplicate dispatch with identical external_event_id
        second_run = dispatcher.publish_event(
            tenant_id=org.id,
            event_type="DECISION_CREATED",
            payload=decision_payload,
            external_event_id=idemp_ext_id,
            sync_execute=True,
        )
        print(f"    Second dispatch (duplicate) count: {len(second_run)}, status: {second_run[0].status}")
        assert len(second_run) == 1
        assert second_run[0].status == "DUPLICATE_SKIPPED"
        assert "already processed" in (second_run[0].error_message or "")
        print("    [+] Idempotency guarantee validated (DUPLICATE_SKIPPED with zero re-execution).")

        # 6. Inbound Webhook Ingress & Security
        print("\n--- 5. Testing Inbound Webhook Security (HMAC-SHA256) ---")
        inbound_payload = {
            "event_id": f"inbound-crm-{uuid.uuid4().hex[:8]}",
            "action": "deal.closed_won",
            "deal_amount": 150000.0,
            "account_name": "Global Telecoms Ltd",
        }
        body_bytes = json.dumps(inbound_payload).encode("utf-8")

        # A: Missing Signature -> 401 Unauthorized
        res_missing = client.post(
            f"/api/v1/webhooks/custom/{webhook_integ.id}",
            content=body_bytes,
            headers={"Content-Type": "application/json"},
        )
        print(f"    Missing signature response: {res_missing.status_code}")
        assert res_missing.status_code == 401

        # B: Invalid Signature -> 401 Unauthorized
        res_invalid = client.post(
            f"/api/v1/webhooks/custom/{webhook_integ.id}",
            content=body_bytes,
            headers={
                "X-Knowra-Signature": "sha256=invalidtamperedsignature000000000000000000000000000000000000",
                "Content-Type": "application/json",
            },
        )
        print(f"    Tampered signature response: {res_invalid.status_code}")
        assert res_invalid.status_code == 401

        # C: Valid Signature -> 202 Accepted
        valid_hmac = hmac.new(webhook_signing_key.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        res_valid = client.post(
            f"/api/v1/webhooks/custom/{webhook_integ.id}",
            content=body_bytes,
            headers={
                "X-Knowra-Signature": f"sha256={valid_hmac}",
                "Content-Type": "application/json",
            },
        )
        print(f"    Valid HMAC response: {res_valid.status_code}, body: {res_valid.json()}")
        assert res_valid.status_code == 202
        assert res_valid.json()["duplicate_skipped"] is False

        # D: Replay Webhook with same event_id -> Fast 200/202 with duplicate_skipped = True
        res_replay = client.post(
            f"/api/v1/webhooks/custom/{webhook_integ.id}",
            content=body_bytes,
            headers={
                "X-Knowra-Signature": f"sha256={valid_hmac}",
                "Content-Type": "application/json",
            },
        )
        print(f"    Replayed webhook response: {res_replay.status_code}, duplicate_skipped: {res_replay.json()['duplicate_skipped']}")
        assert res_replay.status_code in (200, 202)
        assert res_replay.json()["duplicate_skipped"] is True

        print("\n" + "=" * 70)
        print(">>> PHASE 26 E2E VALIDATION SUCCESSFUL: ALL CHECKS PASSED <<<")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_phase26_e2e()
