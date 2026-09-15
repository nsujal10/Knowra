import uuid
import pytest
from app.core.database import SessionLocal
from app.events.dispatcher import EventDispatcher
from app.integrations.models import Integration, IntegrationEvent
from app.models.organization import Organization


def test_event_idempotency_duplicate_skipped():
    """Verify that publishing the exact same external_event_id twice results in DUPLICATE_SKIPPED."""
    db = SessionLocal()
    try:
        # Get or create organization (tenant)
        tenant = db.query(Organization).first()
        if not tenant:
            tenant = Organization(name="Idempotency Test Org", slug=f"idemp-{uuid.uuid4().hex[:6]}")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        dispatcher = EventDispatcher(db)
        ext_event_id = f"test-idemp-{uuid.uuid4().hex[:8]}"

        # First publish
        first_events = dispatcher.publish_event(
            tenant_id=tenant.id,
            event_type="DECISION_CREATED",
            payload={"decision_id": "dec-100", "title": "Adopt PostgreSQL pgvector"},
            external_event_id=ext_event_id,
            sync_execute=True,
        )
        assert len(first_events) >= 1
        assert first_events[0].status in ("COMPLETED", "PENDING", "FAILED")

        # Second publish with the exact same external_event_id
        second_events = dispatcher.publish_event(
            tenant_id=tenant.id,
            event_type="DECISION_CREATED",
            payload={"decision_id": "dec-100", "title": "Adopt PostgreSQL pgvector"},
            external_event_id=ext_event_id,
            sync_execute=True,
        )
        assert len(second_events) == 1
        assert second_events[0].status == "DUPLICATE_SKIPPED"
        assert "Skipped" in (second_events[0].error_message or "")

    finally:
        db.close()
