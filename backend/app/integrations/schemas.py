"""
Phase 26 – Enterprise Integrations & Webhook Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    provider: str = Field(..., description="SLACK | TEAMS | JIRA | WEBHOOK | RESEND | ZOOM | GOOGLE_MEET | LINEAR")
    name: Optional[str] = Field(None, description="Display name for integration")
    credentials_secret: Optional[str] = Field(None, description="API key, OAuth token, or signing secret to be encrypted")
    webhook_url: Optional[str] = Field(None, description="Target external URL for outbound events")
    channel_or_project_id: Optional[str] = Field(None, description="Slack channel ID, Jira project key, or email recipient")
    events_subscribed: List[str] = Field(
        default=["ACTION_CREATED", "DECISION_CONFIRMED", "MEETING_PROCESSED"],
        description="Event types to forward to this integration",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResendTestRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="Resend API Key (re_...)")
    to_email: Optional[str] = Field("delivered@resend.dev", description="Recipient email address")
    meeting_title: Optional[str] = Field("Q3 Strategic Architecture & Executive Review", description="Meeting subject")
    recipient_name: Optional[str] = Field("Executive Team", description="Recipient display name")


class ResendTestResponse(BaseModel):
    success: bool
    email_id: str
    recipient: str
    subject: str
    message: str
    timestamp: datetime


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


class CalendarConnectionStatus(BaseModel):
    provider: str
    name: str
    is_connected: bool
    account_email: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    auto_join: bool = True
    email_summaries: bool = True
    internal_only: bool = False
    events_count: int = 0


class CalendarMeetingItem(BaseModel):
    id: str
    title: str
    provider: str
    start_time: str
    end_time: str
    duration_minutes: int
    meeting_link: Optional[str] = None
    organizer: str
    attendees: List[str] = Field(default_factory=list)
    auto_join: bool = True
    status: str = "SCHEDULED"
    is_external: bool = False


class CalendarConnectRequest(BaseModel):
    provider: str
    account_email: Optional[str] = None
    auto_join: Optional[bool] = True
    email_summaries: Optional[bool] = True


class CalendarToggleBotRequest(BaseModel):
    meeting_id: str
    auto_join: bool


class JiraConnectRequest(BaseModel):
    instance_url: str = Field(..., description="Atlassian instance domain, e.g. softude.atlassian.net")
    email: str = Field(..., description="Atlassian account email")
    api_token: str = Field(..., description="Atlassian API token")
    project_key: Optional[str] = Field("KNOWRA", description="Default Jira project key")


class JiraCreateIssueRequest(BaseModel):
    summary: str = Field(..., description="Issue title/summary")
    description: Optional[str] = Field(None, description="Issue description")
    issue_type: Optional[str] = Field("Task", description="Task, Story, Bug, etc.")
    priority: Optional[str] = Field("Medium", description="High, Medium, Low")

