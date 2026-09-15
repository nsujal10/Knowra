"""
Phase 26 – Enterprise Integrations & Webhook Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    provider: str = Field(..., description="SLACK | TEAMS | JIRA | WEBHOOK")
    name: str = Field(..., min_length=2, max_length=100)
    credentials_secret: str = Field(..., description="API key, OAuth token, or signing secret to be encrypted")
    webhook_url: Optional[str] = Field(None, description="Target external URL for outbound events")
    channel_or_project_id: Optional[str] = Field(None, description="Slack channel ID or Jira project key")
    events_subscribed: List[str] = Field(
        default=["ACTION_CREATED", "DECISION_CONFIRMED"],
        description="Event types to forward to this integration",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    credentials_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    channel_or_project_id: Optional[str] = None
    events_subscribed: Optional[List[str]] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    provider: str
    name: str
    webhook_url: Optional[str] = None
    channel_or_project_id: Optional[str] = None
    events_subscribed: List[str] = Field(default_factory=list)
    status: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class IntegrationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    integration_id: Optional[UUID] = None
    direction: str
    external_event_id: str
    event_type: str
    status: str
    attempt_count: int
    max_retries: int
    payload_json: Dict[str, Any] = Field(default_factory=dict)
    response_status_code: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WebhookReceiptResponse(BaseModel):
    status: str = "ACCEPTED"
    external_event_id: str
    duplicate_skipped: bool = False
    message: str = "Event accepted for processing."


class TestDispatchResponse(BaseModel):
    integration_id: UUID
    event_type: str
    dispatched: bool
    status: str
    detail: str
