"""
Outlook / Microsoft 365 Calendar Integration Service

Handles:
  - Canonical redirect URI generation
  - Microsoft Entra ID / OAuth 2.0 authorization URL generation
  - Authorization code exchange via Microsoft Graph token endpoint
  - User profile retrieval from https://graph.microsoft.com/v1.0/me
  - Token encryption and persistence
  - Live calendar event fetching from Microsoft Graph API v1.0
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration
from app.integrations.schemas import CalendarMeetingItem

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_SCOPES = [
    "Calendars.Read",
    "User.Read",
    "offline_access",
    "openid",
    "profile",
    "email",
]


class OutlookCalendarService:
    def __init__(self):
        self.crypto = SecretEncryptionService()

    def _read_env_val(self, key: str) -> str:
        val = os.getenv(key, "")
        if val:
            return val
        try:
            env_file = Path(__file__).resolve().parents[2].parent / ".env"
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    clean = line.strip()
                    if clean.startswith(f"{key}="):
                        return clean.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
        return ""

    @property
    def client_id(self) -> str:
        return self._read_env_val("MICROSOFT_CLIENT_ID") or settings.MICROSOFT_CLIENT_ID or ""

    @property
    def client_secret(self) -> str:
        return self._read_env_val("MICROSOFT_CLIENT_SECRET") or settings.MICROSOFT_CLIENT_SECRET or ""

    @property
    def tenant_id(self) -> str:
        return self._read_env_val("MICROSOFT_TENANT_ID") or settings.MICROSOFT_TENANT_ID or "common"

    @property
    def authorize_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    def get_redirect_uri(self) -> str:
        custom_uri = self._read_env_val("OUTLOOK_REDIRECT_URI")
        if custom_uri:
            return custom_uri.strip()
        base = (settings.OAUTH_REDIRECT_BASE_URL or "http://localhost:8000").rstrip("/")
        if base.endswith("/api/v1/auth"):
            base = base[: -len("/api/v1/auth")]
        elif base.endswith("/auth"):
            base = base[: -len("/auth")]
        return f"{base}/api/v1/integrations/outlook/callback"

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, tenant_id: str, redirect_uri: Optional[str] = None) -> str:
        r_uri = redirect_uri or self.get_redirect_uri()
        state = json.dumps({"tenant_id": str(tenant_id)})
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": r_uri,
            "response_mode": "query",
            "scope": " ".join(DEFAULT_SCOPES),
            "state": state,
            "prompt": "select_account",
        }
        return f"{self.authorize_endpoint}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchange authorization code for Microsoft Graph tokens."""
        r_uri = redirect_uri or self.get_redirect_uri()
        post_data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": r_uri,
            "scope": " ".join(DEFAULT_SCOPES),
        }).encode("utf-8")

        req = urllib.request.Request(
            self.token_endpoint,
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
                return token_data
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            logger.error(f"Microsoft token exchange error {e.code}: {err}")
            raise RuntimeError(f"Microsoft token exchange failed: {err}")

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Microsoft Graph access token using refresh_token."""
        post_data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(DEFAULT_SCOPES),
        }).encode("utf-8")

        req = urllib.request.Request(
            self.token_endpoint,
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch user profile from Microsoft Graph /v1.0/me."""
        req = urllib.request.Request(
            f"{GRAPH_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Could not fetch Microsoft profile: {e}")
            return {}

    def save_connection(
        self,
        db: Session,
        tenant_id: str | uuid.UUID,
        token_data: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> Integration:
        if isinstance(tenant_id, str):
            try:
                tenant_uuid = uuid.UUID(tenant_id)
            except Exception:
                tenant_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        else:
            tenant_uuid = tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000000")

        account_email = (
            user_profile.get("mail")
            or user_profile.get("userPrincipalName")
            or "user@outlook.com"
        ).lower().strip()
        account_name = user_profile.get("displayName") or "Outlook User"

        encrypted = self.crypto.encrypt(json.dumps(token_data))

        metadata = {
            "account_email": account_email,
            "account_name": account_name,
            "microsoft_user_id": user_profile.get("id"),
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "scope": token_data.get("scope"),
            "expires_in": token_data.get("expires_in"),
        }

        item = (
            db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_uuid,
                Integration.provider == "OUTLOOK",
            )
            .first()
        )
        if not item:
            item = Integration(
                tenant_id=tenant_uuid,
                provider="OUTLOOK",
                name="Outlook Calendar Connector",
                encrypted_credentials=encrypted,
                webhook_url=None,
                channel_or_project_id=account_email,
                events_subscribed=["MEETING_PROCESSED"],
                status="ACTIVE",
                metadata_json=metadata,
            )
            db.add(item)
        else:
            item.status = "ACTIVE"
            item.encrypted_credentials = encrypted
            item.channel_or_project_id = account_email
            item.metadata_json = {**(item.metadata_json or {}), **metadata}

        db.commit()
        db.refresh(item)
        return item

    async def fetch_live_events(
        self, db: Session, tenant_id: str | uuid.UUID
    ) -> List[CalendarMeetingItem]:
        """Fetch real live calendar events from Microsoft Graph API v1.0."""
        if isinstance(tenant_id, str):
            try:
                tenant_uuid = uuid.UUID(tenant_id)
            except Exception:
                tenant_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        else:
            tenant_uuid = tenant_id

        integration = (
            db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_uuid,
                Integration.provider == "OUTLOOK",
                Integration.status == "ACTIVE",
            )
            .first()
        )
        if not integration or not integration.encrypted_credentials:
            return []

        try:
            raw_tokens = self.crypto.decrypt(integration.encrypted_credentials)
            tokens = json.loads(raw_tokens)
        except Exception as e:
            logger.error(f"Failed to decrypt Outlook credentials: {e}")
            return []

        access_token = tokens.get("access_token")
        refresh_token_str = tokens.get("refresh_token")

        events_url = (
            f"{GRAPH_BASE}/me/calendar/events?"
            "$select=id,subject,start,end,location,attendees,onlineMeeting,webLink,organizer&"
            "$top=25&$orderby=start/dateTime"
        )

        def _call_graph(tok: str) -> Dict[str, Any]:
            req = urllib.request.Request(
                events_url,
                headers={"Authorization": f"Bearer {tok}", "Prefer": 'outlook.timezone="UTC"'},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode("utf-8"))

        data = None
        try:
            data = _call_graph(access_token)
        except urllib.error.HTTPError as e:
            if e.code == 401 and refresh_token_str:
                logger.info("Outlook access token expired, refreshing...")
                try:
                    new_tokens = self.refresh_access_token(refresh_token_str)
                    merged = {**tokens, **new_tokens}
                    integration.encrypted_credentials = self.crypto.encrypt(json.dumps(merged))
                    db.commit()
                    access_token = merged["access_token"]
                    data = _call_graph(access_token)
                except Exception as ref_err:
                    logger.error(f"Failed to refresh Outlook token: {ref_err}")
                    return []
            else:
                logger.error(f"Microsoft Graph events API error {e.code}: {e}")
                return []
        except Exception as e:
            logger.error(f"Error calling Microsoft Graph API: {e}")
            return []

        if not data or "value" not in data:
            return []

        items: List[CalendarMeetingItem] = []
        for evt in data.get("value", []):
            start_obj = evt.get("start", {})
            end_obj = evt.get("end", {})
            start_str = start_obj.get("dateTime", "")
            end_str = end_obj.get("dateTime", "")

            diff_mins = 30
            try:
                if start_str and end_str:
                    s_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    e_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    diff_mins = max(15, int((e_dt - s_dt).total_seconds() / 60))
            except Exception:
                diff_mins = 30

            attendees_raw = evt.get("attendees", [])
            attendee_emails = [
                a.get("emailAddress", {}).get("address", "")
                for a in attendees_raw
                if a.get("emailAddress", {}).get("address")
            ]

            organizer_info = evt.get("organizer", {}).get("emailAddress", {})
            organizer_str = organizer_info.get("name") or organizer_info.get("address") or "Organizer"

            meeting_link = None
            online_meeting = evt.get("onlineMeeting")
            if online_meeting and online_meeting.get("joinUrl"):
                meeting_link = online_meeting["joinUrl"]
            elif evt.get("webLink"):
                meeting_link = evt["webLink"]

            items.append(
                CalendarMeetingItem(
                    id=str(evt.get("id")),
                    title=evt.get("subject") or "Untitled Outlook Meeting",
                    provider="OUTLOOK",
                    start_time=start_str,
                    end_time=end_str,
                    duration_minutes=diff_mins,
                    meeting_link=meeting_link,
                    organizer=organizer_str,
                    attendees=attendee_emails,
                    auto_join=True,
                    status="SCHEDULED",
                    is_external=False,
                )
            )

        return items


outlook_service = OutlookCalendarService()
