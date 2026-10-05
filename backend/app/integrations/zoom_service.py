"""
Zoom OAuth 2.0 Integration Service

Handles:
  - Canonical redirect URI generation
  - Authorization URL creation
  - Authorization code exchange (Basic Auth)
  - Profile retrieval from Zoom API v2
  - Credential encryption and database persistence
"""

import base64
import json
import logging
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration
from app.integrations.schemas import CalendarMeetingItem

logger = logging.getLogger(__name__)


class ZoomIntegrationService:
    ZOOM_AUTH_BASE = "https://zoom.us/oauth/authorize"
    ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
    ZOOM_API_BASE = "https://api.zoom.us/v2"

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
        return self._read_env_val("ZOOM_CLIENT_ID") or settings.ZOOM_CLIENT_ID or ""

    @property
    def client_secret(self) -> str:
        return self._read_env_val("ZOOM_CLIENT_SECRET") or settings.ZOOM_CLIENT_SECRET or ""

    def get_redirect_uri(self) -> str:
        custom_uri = self._read_env_val("ZOOM_REDIRECT_URI") or settings.ZOOM_REDIRECT_URI
        if custom_uri:
            return custom_uri.strip()
        base = (settings.OAUTH_REDIRECT_BASE_URL or "http://localhost:8000").rstrip("/")
        if base.endswith("/api/v1/auth"):
            base = base[: -len("/api/v1/auth")]
        elif base.endswith("/auth"):
            base = base[: -len("/auth")]
        return f"{base}/api/v1/integrations/zoom/callback"

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_auth_url(self, state: Optional[str] = None) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.get_redirect_uri(),
        }
        if state:
            params["state"] = state
        return f"{self.ZOOM_AUTH_BASE}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for Zoom access and refresh tokens.
        Zoom requires HTTP Basic Auth with client_id:client_secret.
        """
        creds = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic_auth = base64.b64encode(creds).decode("utf-8")

        post_data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.get_redirect_uri(),
        }).encode("utf-8")

        req = urllib.request.Request(
            self.ZOOM_TOKEN_URL,
            data=post_data,
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Zoom token exchange HTTPError {e.code}: {error_body}")
            raise RuntimeError(f"Zoom token exchange failed: {error_body}")
        except Exception as e:
            logger.error(f"Zoom token exchange error: {e}")
            raise

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch basic user info from Zoom API v2 /users/me."""
        req = urllib.request.Request(
            f"{self.ZOOM_API_BASE}/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Could not fetch Zoom user profile: {e}")
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

        account_email = user_profile.get("email") or "connected@zoom.us"
        account_name = f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip() or "Zoom User"

        encrypted = self.crypto.encrypt(json.dumps(token_data))

        metadata = {
            "account_email": account_email,
            "account_name": account_name,
            "zoom_user_id": user_profile.get("id"),
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "scope": token_data.get("scope"),
            "expires_in": token_data.get("expires_in"),
        }

        item = (
            db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_uuid,
                Integration.provider == "ZOOM",
            )
            .first()
        )
        if not item:
            item = Integration(
                tenant_id=tenant_uuid,
                provider="ZOOM",
                name="Zoom Meeting Intelligence",
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

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Zoom access token using HTTP Basic Auth."""
        creds = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic_auth = base64.b64encode(creds).decode("utf-8")

        post_data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.ZOOM_TOKEN_URL,
            data=post_data,
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    async def fetch_live_events(
        self, db: Session, tenant_id: str | uuid.UUID
    ) -> List[CalendarMeetingItem]:
        """Fetch real live meetings from Zoom API v2."""
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
                Integration.provider == "ZOOM",
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
            logger.error(f"Failed to decrypt Zoom credentials: {e}")
            return []

        access_token = tokens.get("access_token")
        refresh_token_str = tokens.get("refresh_token")

        meetings_url = f"{self.ZOOM_API_BASE}/users/me/meetings?type=upcoming&page_size=30"

        def _call_zoom(tok: str) -> Dict[str, Any]:
            req = urllib.request.Request(
                meetings_url,
                headers={"Authorization": f"Bearer {tok}"},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode("utf-8"))

        data = None
        try:
            data = _call_zoom(access_token)
        except urllib.error.HTTPError as e:
            if e.code == 401 and refresh_token_str:
                logger.info("Zoom access token expired, refreshing...")
                try:
                    new_tokens = self.refresh_access_token(refresh_token_str)
                    merged = {**tokens, **new_tokens}
                    integration.encrypted_credentials = self.crypto.encrypt(json.dumps(merged))
                    db.commit()
                    access_token = merged["access_token"]
                    data = _call_zoom(access_token)
                except Exception as ref_err:
                    logger.error(f"Failed to refresh Zoom token: {ref_err}")
                    return []
            else:
                logger.error(f"Zoom meetings API error {e.code}: {e}")
                return []
        except Exception as e:
            logger.error(f"Error calling Zoom meetings API: {e}")
            return []

        if not data or "meetings" not in data:
            return []

        items: List[CalendarMeetingItem] = []
        account_email = integration.channel_or_project_id or "Zoom Host"

        for mtg in data.get("meetings", []):
            start_str = mtg.get("start_time", "")
            duration = mtg.get("duration", 30)

            end_str = ""
            try:
                if start_str:
                    s_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    e_dt = s_dt + timedelta(minutes=duration)
                    end_str = e_dt.isoformat()
            except Exception:
                end_str = start_str

            items.append(
                CalendarMeetingItem(
                    id=str(mtg.get("id")),
                    title=mtg.get("topic") or "Untitled Zoom Meeting",
                    provider="ZOOM",
                    start_time=start_str,
                    end_time=end_str,
                    duration_minutes=duration,
                    meeting_link=mtg.get("join_url"),
                    organizer=account_email,
                    attendees=[account_email],
                    auto_join=True,
                    status="SCHEDULED",
                    is_external=False,
                )
            )

        return items


zoom_service = ZoomIntegrationService()

