"""
Google Calendar OAuth 2.0 & Live Calendar Sync Service

Handles:
  1. OAuth 2.0 Authorization URL generation with offline calendar scopes
  2. Authorization Code exchange for Access & Refresh Tokens
  3. AES-256 Token Encryption & Storage in Database
  4. Live Google Calendar API v3 Event Fetching (primary calendar)
  5. Automatic Token Refresh on Expiry
  6. Development Sandbox Fallback for local environments
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent
from app.integrations.schemas import CalendarConnectionStatus, CalendarMeetingItem

logger = logging.getLogger("knowra.google_calendar")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_CALENDAR_EVENTS_ENDPOINT = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "profile",
]


class GoogleCalendarService:
    def __init__(self):
        self.crypto = SecretEncryptionService()
        self.frontend_url = settings.FRONTEND_URL or "http://localhost:3000"

    @property
    def client_id(self) -> str:
        return settings.GOOGLE_CLIENT_ID or ""

    @property
    def client_secret(self) -> str:
        return settings.GOOGLE_CLIENT_SECRET or ""

    @property
    def is_configured(self) -> bool:
        """Checks if real Google OAuth 2.0 Client credentials are set in configuration."""
        return bool(self.client_id and self.client_secret)

    def get_redirect_uri(self) -> str:
        """
        Computes the canonical authorized redirect URI for Google Calendar OAuth 2.0.
        Ensures /api/v1/integrations/google-calendar/callback is consistently used.
        """
        base = (settings.OAUTH_REDIRECT_BASE_URL or "http://localhost:8000").rstrip("/")
        for sub in ("/api/v1/auth", "/api/v1", "/auth"):
            if base.endswith(sub):
                base = base[:-len(sub)]
        return f"{base}/api/v1/integrations/google-calendar/callback"

    def get_authorization_url(self, tenant_id: str, redirect_uri: Optional[str] = None, state_extra: Optional[str] = None) -> str:
        """
        Builds Google OAuth 2.0 authorization URL with offline access to retrieve a refresh token.
        """
        effective_redirect = redirect_uri or self.get_redirect_uri()
        state_payload = {
            "tenant_id": str(tenant_id),
            "nonce": secrets.token_hex(8),
            "extra": state_extra or "",
        }
        state = json.dumps(state_payload)

        params = {
            "client_id": self.client_id,
            "redirect_uri": effective_redirect,
            "response_type": "code",
            "scope": " ".join(CALENDAR_SCOPES),
            "access_type": "offline",
            "prompt": "consent select_account",
            "include_granted_scopes": "true",
            "state": state,
        }
        return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code with Google for access and refresh tokens.
        """
        if not self.is_configured:
            raise ValueError("Google OAuth Client ID and Secret are not configured in backend settings.")

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )

            if token_resp.status_code != 200:
                logger.error(f"Google token exchange failed: {token_resp.text}")
                raise ValueError(f"Failed to exchange Google OAuth code: {token_resp.text}")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            # Fetch authenticated user profile (email and name)
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_info = userinfo_resp.json() if userinfo_resp.status_code == 200 else {}

            return {
                "token_data": token_data,
                "user_info": user_info,
            }

    async def refresh_access_token_if_needed(self, credentials: Dict[str, Any]) -> str:
        """
        Checks token expiration and refreshes if necessary using the stored refresh token.
        """
        access_token = credentials.get("access_token", "")
        refresh_token = credentials.get("refresh_token", "")
        expires_at = credentials.get("expires_at", 0)

        # Buffer of 60 seconds
        if time.time() < (expires_at - 60):
            return access_token

        if not refresh_token:
            return access_token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    GOOGLE_TOKEN_ENDPOINT,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    new_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    credentials["access_token"] = new_token
                    credentials["expires_at"] = time.time() + expires_in
                    return new_token
        except Exception as e:
            logger.warning(f"Could not refresh Google access token: {e}")

        return access_token

    def save_connection(
        self,
        db: Session,
        tenant_id: UUID | str,
        account_email: str,
        token_data: Dict[str, Any],
        auto_join: bool = True,
        email_summaries: bool = True,
    ) -> Integration:
        """
        Encrypts token credentials using AES-256 and persists to the database.
        """
        try:
            tenant_uuid = UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        except (ValueError, TypeError, AttributeError):
            import uuid as py_uuid
            tenant_uuid = py_uuid.uuid5(py_uuid.NAMESPACE_DNS, str(tenant_id or "knowra-default-tenant"))

        # Prepare credentials bundle with calculated expires_at
        expires_in = token_data.get("expires_in", 3600)
        credentials_bundle = {
            "access_token": token_data.get("access_token", ""),
            "refresh_token": token_data.get("refresh_token", ""),
            "token_type": token_data.get("token_type", "Bearer"),
            "scope": token_data.get("scope", ""),
            "expires_at": time.time() + expires_in,
        }

        encrypted = self.crypto.encrypt(json.dumps(credentials_bundle))

        item = (
            db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_uuid,
                Integration.provider == "GOOGLE_CALENDAR",
            )
            .first()
        )

        metadata = {
            "account_email": account_email,
            "auto_join": auto_join,
            "email_summaries": email_summaries,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "real_oauth": True,
            "synced_events_count": 0,
        }

        if not item:
            item = Integration(
                tenant_id=tenant_uuid,
                provider="GOOGLE_CALENDAR",
                name="Google Calendar Connector",
                encrypted_credentials=encrypted,
                webhook_url=None,
                channel_or_project_id=account_email,
                events_subscribed=["MEETING_PROCESSED", "ACTION_CREATED", "DECISION_CONFIRMED"],
                status="ACTIVE",
                metadata_json=metadata,
            )
            db.add(item)
        else:
            item.status = "ACTIVE"
            item.encrypted_credentials = encrypted
            item.channel_or_project_id = account_email
            item.metadata_json = {**(item.metadata_json or {}), **metadata}

        # Also activate Google Meet since it shares the same Google Workspace account
        meet_item = (
            db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_uuid,
                Integration.provider == "GOOGLE_MEET",
            )
            .first()
        )
        if not meet_item:
            meet_item = Integration(
                tenant_id=tenant_uuid,
                provider="GOOGLE_MEET",
                name="Google Meet Notetaker",
                encrypted_credentials=encrypted,
                webhook_url=None,
                channel_or_project_id=account_email,
                events_subscribed=["MEETING_PROCESSED"],
                status="ACTIVE",
                metadata_json=metadata,
            )
            db.add(meet_item)
        else:
            meet_item.status = "ACTIVE"
            meet_item.encrypted_credentials = encrypted
            meet_item.channel_or_project_id = account_email
            meet_item.metadata_json = {**(meet_item.metadata_json or {}), **metadata}

        ev = IntegrationEvent(
            tenant_id=tenant_uuid,
            integration_id=item.id if item.id else None,
            direction="INBOUND",
            external_event_id=f"gcal_{secrets.token_hex(6)}",
            event_type="GOOGLE_CALENDAR_CONNECTED",
            status="COMPLETED",
            attempt_count=1,
            max_retries=3,
            payload_json={"provider": "GOOGLE_CALENDAR", "email": account_email, "mode": "OAUTH2"},
            response_status_code=200,
        )
        db.add(ev)
        db.commit()
        db.refresh(item)
        return item

    async def fetch_live_events(self, db: Session, tenant_id: UUID | str) -> List[CalendarMeetingItem]:
        """
        Calls Google Calendar API v3 to fetch real upcoming calendar events from the user's primary calendar.
        """
        tenant_uuid = UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        item = (
            db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_uuid,
                Integration.provider == "GOOGLE_CALENDAR",
                Integration.status == "ACTIVE",
            )
            .first()
        )

        if not item or not item.encrypted_credentials:
            return []

        # Decrypt stored credentials
        try:
            raw_creds = self.crypto.decrypt(item.encrypted_credentials)
            credentials = json.loads(raw_creds)
        except Exception as e:
            logger.error(f"Failed to decrypt Google Calendar credentials: {e}")
            return []

        access_token = await self.refresh_access_token_if_needed(credentials)
        if not access_token:
            return []

        # Fetch events from now onwards
        time_min = datetime.now(timezone.utc).isoformat()
        params = {
            "timeMin": time_min,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 25,
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    GOOGLE_CALENDAR_EVENTS_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    google_items = data.get("items", [])
                    events: List[CalendarMeetingItem] = []

                    meta = item.metadata_json or {}
                    auto_join_pref = meta.get("auto_join", True)

                    for g_evt in google_items:
                        title = g_evt.get("summary") or "Untitled Meeting"
                        start_info = g_evt.get("start", {})
                        end_info = g_evt.get("end", {})

                        start_dt = start_info.get("dateTime") or start_info.get("date") or time_min
                        end_dt = end_info.get("dateTime") or end_info.get("date")

                        diff_mins = 30
                        try:
                            s = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                            e = datetime.fromisoformat(end_dt.replace("Z", "+00:00")) if end_dt else s + timedelta(minutes=30)
                            diff_mins = max(1, int((e - s).total_seconds() / 60))
                        except Exception:
                            pass

                        # Detect Meet / Teams / Zoom links
                        meet_url = g_evt.get("hangoutLink")
                        if not meet_url:
                            for entry in g_evt.get("conferenceData", {}).get("entryPoints", []):
                                if entry.get("uri"):
                                    meet_url = entry["uri"]
                                    break

                        organizer_email = g_evt.get("organizer", {}).get("email") or meta.get("account_email") or "user@domain.com"
                        attendees_raw = g_evt.get("attendees", [])
                        attendee_emails = [a.get("email") for a in attendees_raw if a.get("email")]

                        # Format human friendly start and end times
                        start_time_fmt = start_dt
                        end_time_fmt = end_dt or start_dt
                        try:
                            s_obj = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                            e_obj = datetime.fromisoformat(end_dt.replace("Z", "+00:00")) if end_dt else s_obj + timedelta(minutes=diff_mins)
                            now_date = datetime.now(timezone.utc).date()
                            if s_obj.date() == now_date:
                                day_prefix = "Today"
                            elif s_obj.date() == now_date + timedelta(days=1):
                                day_prefix = "Tomorrow"
                            else:
                                day_prefix = s_obj.strftime("%a, %b %d")
                            start_time_fmt = f"{day_prefix}, {s_obj.strftime('%I:%M %p')}"
                            end_time_fmt = e_obj.strftime("%I:%M %p")
                        except Exception:
                            pass

                        events.append(
                            CalendarMeetingItem(
                                id=f"gcal_{g_evt.get('id', secrets.token_hex(6))}",
                                title=title,
                                provider="GOOGLE_CALENDAR",
                                start_time=start_time_fmt,
                                end_time=end_time_fmt,
                                duration_minutes=diff_mins,
                                meeting_link=meet_url,
                                organizer=organizer_email,
                                attendees=attendee_emails or [organizer_email],
                                auto_join=auto_join_pref,
                                status="SCHEDULED",
                                is_external=False,
                            )
                        )

                    # Update synced count in integration metadata
                    meta["synced_events_count"] = len(events)
                    meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
                    item.metadata_json = meta
                    db.commit()

                    return events
                else:
                    logger.warning(f"Google Calendar API returned status {resp.status_code}: {resp.text}")
        except Exception as ex:
            logger.error(f"Error calling Google Calendar API: {ex}")

        return []


google_calendar_service = GoogleCalendarService()
