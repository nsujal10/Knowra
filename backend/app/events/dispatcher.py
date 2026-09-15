"""
Phase 26 – Central Domain Event Dispatcher

Decouples internal system state changes (ActionItems created, Decisions confirmed,
Meetings processed) from external third-party syncs (Slack, Teams, Jira, Webhooks).
Guarantees idempotency and enqueues Celery background tasks.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
import structlog

from app.integrations.models import Integration, IntegrationEvent

logger = structlog.get_logger(__name__)


class EventDispatcher:
    """
    Publish/Subscribe Domain Event Bus for Knowra.
    Routes internal events to registered integration channels and enqueues Celery tasks.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def is_event_duplicate(self, tenant_id: UUID, external_event_id: str) -> bool:
        """Verifies whether an external event has already been registered to enforce idempotency."""
        from sqlalchemy import or_
        existing = (
            self.db.query(IntegrationEvent)
            .filter(
                IntegrationEvent.tenant_id == tenant_id,
                or_(
                    IntegrationEvent.external_event_id == external_event_id,
                    IntegrationEvent.external_event_id.like(f"{external_event_id}%"),
                ),
            )
            .first()
        )
        return existing is not None


    def publish_event(
        self,
        tenant_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
        external_event_id: Optional[str] = None,
        sync_execute: bool = False,
    ) -> List[IntegrationEvent]:
        """
        Publishes a domain event across all matching active tenant integrations.
        Enforces idempotency and triggers background delivery.
        """
        evt_id = external_event_id or f"evt_{event_type.lower()}_{uuid.uuid4().hex[:12]}"

        # Check idempotency
        if self.is_event_duplicate(tenant_id, evt_id):
            logger.warning(
                "Duplicate event ignored for idempotency",
                tenant_id=str(tenant_id),
                external_event_id=evt_id,
                event_type=event_type,
            )
            dup_record = IntegrationEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                external_event_id=evt_id,
                event_type=event_type,
                status="DUPLICATE_SKIPPED",
                payload_json=payload,
                direction="OUTBOUND",
                error_message="Skipped: external_event_id already processed.",
            )
            return [dup_record]


        # Find matching active integrations for this tenant
        integrations = (
            self.db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_id,
                Integration.status == "ACTIVE",
            )
            .all()
        )

        matched_integrations = [
            i for i in integrations
            if event_type in (i.events_subscribed or []) or "*" in (i.events_subscribed or [])
        ]

        created_events: List[IntegrationEvent] = []

        if not matched_integrations:
            # Record general event even without specific integration target
            evt = IntegrationEvent(
                tenant_id=tenant_id,
                integration_id=None,
                direction="OUTBOUND",
                external_event_id=evt_id,
                event_type=event_type,
                status="COMPLETED",
                payload_json=payload,
            )
            self.db.add(evt)
            created_events.append(evt)
        else:
            for integ in matched_integrations:
                # Per-integration event tracking
                channel_evt_id = f"{evt_id}_{integ.id.hex[:6]}"
                evt = IntegrationEvent(
                    tenant_id=tenant_id,
                    integration_id=integ.id,
                    direction="OUTBOUND",
                    external_event_id=channel_evt_id,
                    event_type=event_type,
                    status="PENDING",
                    payload_json=payload,
                )
                self.db.add(evt)
                created_events.append(evt)

        self.db.commit()
        for e in created_events:
            self.db.refresh(e)

        # Trigger delivery
        for e in created_events:
            if e.integration_id and e.status == "PENDING":
                if sync_execute:
                    from app.workers.integrations import execute_integration_dispatch_sync
                    execute_integration_dispatch_sync(self.db, e.id)
                else:
                    try:
                        from app.workers.integrations import dispatch_integration_event_task
                        dispatch_integration_event_task.delay(str(e.id))
                    except Exception as err:
                        logger.warning(
                            "Celery queue unavailable, falling back to sync dispatch",
                            event_id=str(e.id),
                            error=str(err),
                        )
                        from app.workers.integrations import execute_integration_dispatch_sync
                        execute_integration_dispatch_sync(self.db, e.id)

        return created_events
