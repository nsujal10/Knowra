"""
Phase 26 – Enterprise Integrations Management API Endpoints

Provides authenticated endpoints for:
  - Provisioning third-party integrations (Slack, Teams, Jira, Webhooks)
  - Managing encrypted connection secrets
  - Outbound event dispatch history
  - Manual test dispatch verification
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.events.dispatcher import EventDispatcher
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationEventResponse,
    IntegrationResponse,
    IntegrationUpdate,
    TestDispatchResponse,
)
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter()


@router.get(
    "",
    response_model=List[IntegrationResponse],
    summary="List configured third-party integrations for tenant",
)
def list_integrations(
    provider: Optional[str] = Query(None, description="Filter by provider (SLACK, TEAMS, JIRA, WEBHOOK)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE)"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[IntegrationResponse]:
    tenant_id = current_user.organization_id
    q = db.query(Integration).filter(Integration.tenant_id == tenant_id)
    if provider:
        q = q.filter(Integration.provider == provider.upper())
    if status_filter:
        q = q.filter(Integration.status == status_filter.upper())
    items = q.order_by(Integration.created_at.desc()).all()
    return [IntegrationResponse.model_validate(i) for i in items]


@router.post(
    "",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new third-party integration with encrypted credentials",
)
def create_integration(
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> IntegrationResponse:
    tenant_id = current_user.organization_id
    crypto = SecretEncryptionService()
    encrypted_secret = crypto.encrypt(payload.credentials_secret)

    item = Integration(
        tenant_id=tenant_id,
        provider=payload.provider.upper(),
        name=payload.name,
        encrypted_credentials=encrypted_secret,
        webhook_url=payload.webhook_url,
        channel_or_project_id=payload.channel_or_project_id,
        events_subscribed=[e.upper() for e in payload.events_subscribed],
        status="ACTIVE",
        metadata_json=payload.metadata,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return IntegrationResponse.model_validate(item)


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Retrieve single integration details",
)
def get_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> IntegrationResponse:
    tenant_id = current_user.organization_id
    item = (
        db.query(Integration)
        .filter(Integration.id == integration_id, Integration.tenant_id == tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    return IntegrationResponse.model_validate(item)


@router.patch(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Update integration settings or rotate credentials",
)
def update_integration(
    integration_id: UUID,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> IntegrationResponse:
    tenant_id = current_user.organization_id
    item = (
        db.query(Integration)
        .filter(Integration.id == integration_id, Integration.tenant_id == tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    if payload.name is not None:
        item.name = payload.name
    if payload.credentials_secret is not None:
        crypto = SecretEncryptionService()
        item.encrypted_credentials = crypto.encrypt(payload.credentials_secret)
    if payload.webhook_url is not None:
        item.webhook_url = payload.webhook_url
    if payload.channel_or_project_id is not None:
        item.channel_or_project_id = payload.channel_or_project_id
    if payload.events_subscribed is not None:
        item.events_subscribed = [e.upper() for e in payload.events_subscribed]
    if payload.status is not None:
        item.status = payload.status.upper()
    if payload.metadata is not None:
        item.metadata_json = payload.metadata

    db.commit()
    db.refresh(item)
    return IntegrationResponse.model_validate(item)


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an integration configuration",
)
def delete_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    tenant_id = current_user.organization_id
    item = (
        db.query(Integration)
        .filter(Integration.id == integration_id, Integration.tenant_id == tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    db.delete(item)
    db.commit()


@router.post(
    "/{integration_id}/test",
    response_model=TestDispatchResponse,
    summary="Trigger a test event dispatch to verify integration connectivity",
)
def test_integration_dispatch(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> TestDispatchResponse:
    tenant_id = current_user.organization_id
    item = (
        db.query(Integration)
        .filter(Integration.id == integration_id, Integration.tenant_id == tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    dispatcher = EventDispatcher(db=db)
    test_payload = {
        "event": "TEST_CONNECTIVITY",
        "message": "Knowra Integration Connectivity Verification Ping",
        "integration_name": item.name,
    }
    events = dispatcher.publish_event(
        tenant_id=tenant_id,
        event_type="TEST_PING",
        payload=test_payload,
        sync_execute=True,
    )

    dispatched = any(e.status == "COMPLETED" for e in events)
    return TestDispatchResponse(
        integration_id=item.id,
        event_type="TEST_PING",
        dispatched=dispatched,
        status="COMPLETED" if dispatched else "PENDING",
        detail=f"Dispatched test ping to {item.provider} ({item.name})",
    )


@router.get(
    "/events/history",
    response_model=List[IntegrationEventResponse],
    summary="List recent integration events and delivery statuses",
)
def list_event_history(
    integration_id: Optional[UUID] = Query(None, description="Filter by integration"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[IntegrationEventResponse]:
    tenant_id = current_user.organization_id
    q = db.query(IntegrationEvent).filter(IntegrationEvent.tenant_id == tenant_id)
    if integration_id:
        q = q.filter(IntegrationEvent.integration_id == integration_id)
    events = q.order_by(IntegrationEvent.created_at.desc()).limit(limit).all()
    return [IntegrationEventResponse.model_validate(e) for e in events]
