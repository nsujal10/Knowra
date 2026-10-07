"""
Atlassian Jira REST API v3 Integration Service

Handles:
  - Canonical Atlassian instance URL normalization (e.g. knowra-team.atlassian.net)
  - Credential verification via Basic Auth (API Token) with intelligent email resolution
  - Live projects discovery via /rest/api/3/project/search
  - Real Jira sprint issue synchronization via /rest/api/3/search/jql
  - Direct issue creation from meeting action items (ADF v3 format)
  - Credential encryption and database persistence
"""

import base64
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent

logger = logging.getLogger(__name__)


class JiraIntegrationService:
    def __init__(self):
        self.crypto = SecretEncryptionService()

    @staticmethod
    def normalize_instance_url(url: str) -> str:
        """Ensure the Atlassian instance URL has proper https scheme and no trailing slash."""
        clean = (url or "").strip().lower()
        if not clean:
            raise ValueError("Jira instance URL or domain is required.")
        
        # If user entered just subdomain 'knowra-team' or 'softude'
        if not ("." in clean or "/" in clean):
            clean = f"https://{clean}.atlassian.net"
        elif not clean.startswith("http://") and not clean.startswith("https://"):
            clean = f"https://{clean}"
            
        return clean.rstrip("/")

    @staticmethod
    def get_auth_header(email: str, api_token: str) -> str:
        auth_bytes = f"{email.strip()}:{api_token.strip()}".encode("utf-8")
        return f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

    def _execute_myself_request(self, norm_url: str, email: str, api_token: str) -> Dict[str, Any]:
        """Query /rest/api/3/myself with given credentials."""
        endpoint = f"{norm_url}/rest/api/3/myself"
        auth_header = self.get_auth_header(email, api_token)

        req = urllib.request.Request(
            endpoint,
            headers={
                "Authorization": auth_header,
                "Accept": "application/json",
                "User-Agent": "Knowra-Intelligence/1.0",
            },
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return {
                "valid": True,
                "account_id": data.get("accountId"),
                "display_name": data.get("displayName") or email,
                "email": data.get("emailAddress") or email,
                "avatar_url": (data.get("avatarUrls") or {}).get("48x48"),
                "instance_url": norm_url,
            }

    def verify_credentials(self, instance_url: str, email: str, api_token: str) -> Dict[str, Any]:
        """Verify Atlassian credentials by querying /rest/api/3/myself with automatic fallback to configured email."""
        norm_url = self.normalize_instance_url(instance_url)

        # Allow test/demo mock tokens if present
        if api_token.strip().startswith("demo_") or api_token.strip() == "jira_demo_token_knowra_live":
            return {
                "valid": True,
                "account_id": f"acc_{uuid.uuid4().hex[:8]}",
                "display_name": (email or "Jira User").split("@")[0].replace(".", " ").title(),
                "email": email.strip() if email else "jira@knowra.ai",
                "avatar_url": None,
                "instance_url": norm_url,
            }

        candidate_emails = []
        if email and email.strip():
            candidate_emails.append(email.strip())
        configured_email = (getattr(settings, "JIRA_API_EMAIL", None) or "").strip()
        if configured_email and configured_email not in candidate_emails:
            candidate_emails.append(configured_email)

        last_error = None
        for cand_email in candidate_emails:
            try:
                res = self._execute_myself_request(norm_url, cand_email, api_token)
                logger.info("Jira authentication succeeded with account: %s", cand_email)
                return res
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.warning("Jira authentication failed HTTP %d for '%s': %s", e.code, cand_email, err_body[:100])
                last_error = e
                if e.code == 404:
                    raise ValueError(
                        f"Jira site '{norm_url}' was not found (HTTP 404). "
                        "Please verify your JIRA_INSTANCE_URL in .env (e.g. https://your-company.atlassian.net)."
                    )
            except urllib.error.URLError as e:
                logger.error("Jira network error connecting to %s: %s", norm_url, e.reason)
                raise ValueError(f"Could not reach Jira instance at {norm_url}. Check the URL and your connection.")
            except Exception as e:
                last_error = e

        if last_error and isinstance(last_error, urllib.error.HTTPError) and last_error.code in (401, 403):
            raise ValueError(
                "Authentication failed (HTTP 401). Please verify your Atlassian account email and API token."
            )
        raise ValueError(f"Failed to connect to Jira: {str(last_error or 'Invalid credentials')}")

    def fetch_projects(self, instance_url: str, email: str, api_token: str) -> List[Dict[str, Any]]:
        """Fetch accessible projects from /rest/api/3/project/search."""
        norm_url = self.normalize_instance_url(instance_url)

        if api_token.strip().startswith("demo_") or api_token.strip() == "jira_demo_token_knowra_live":
            return [
                {"id": "10000", "key": "SCRUM", "name": "Knowra Scrum Team", "projectTypeKey": "software"},
            ]

        eff_email = email.strip() if email else (getattr(settings, "JIRA_API_EMAIL", "") or "")
        endpoint = f"{norm_url}/rest/api/3/project/search?maxResults=50"
        auth_header = self.get_auth_header(eff_email, api_token)

        req = urllib.request.Request(
            endpoint,
            headers={
                "Authorization": auth_header,
                "Accept": "application/json",
                "User-Agent": "Knowra-Intelligence/1.0",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
                values = data.get("values", [])
                return [
                    {
                        "id": p.get("id"),
                        "key": p.get("key"),
                        "name": p.get("name"),
                        "projectTypeKey": p.get("projectTypeKey", "software"),
                        "avatar_url": (p.get("avatarUrls") or {}).get("32x32"),
                    }
                    for p in values
                ]
        except Exception as e:
            logger.warning("Could not fetch projects from Jira: %s", str(e))
            return []

    def save_connection(
        self,
        tenant_id: uuid.UUID,
        instance_url: str,
        email: str,
        api_token: str,
        project_key: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Verify, encrypt, and persist Jira credentials in the tenant integration record."""
        # 1. Verify credentials with Atlassian API (resolves verified email)
        profile = self.verify_credentials(instance_url, email, api_token)
        norm_url = profile["instance_url"]
        verified_email = profile["email"]
        
        # 2. Fetch projects and validate project key
        projects = self.fetch_projects(norm_url, verified_email, api_token)
        real_keys = [p["key"].upper() for p in projects]
        
        req_key = (project_key or "").strip().upper()
        if req_key and req_key in real_keys:
            clean_project_key = req_key
        elif real_keys:
            # Auto-assign the first discovered active Jira project (e.g. SCRUM)
            clean_project_key = real_keys[0]
        else:
            clean_project_key = req_key or getattr(settings, "JIRA_DEFAULT_PROJECT_KEY", "SCRUM")

        project_obj = next((p for p in projects if p.get("key", "").upper() == clean_project_key), None)
        project_name = project_obj.get("name") if project_obj else f"Project {clean_project_key}"

        # 3. Encrypt credentials
        secret_payload = {
            "instance_url": norm_url,
            "email": verified_email,
            "api_token": api_token.strip(),
            "project_key": clean_project_key,
        }
        encrypted_secret = self.crypto.encrypt(json.dumps(secret_payload))

        # 4. Upsert Integration record
        item = (
            db.query(Integration)
            .filter(Integration.tenant_id == tenant_id, Integration.provider == "JIRA")
            .first()
        )

        meta = {
            "instance_url": norm_url,
            "account_id": profile.get("account_id"),
            "display_name": profile.get("display_name"),
            "email": verified_email,
            "account_email": verified_email,
            "project_key": clean_project_key,
            "project_name": project_name,
            "avatar_url": profile.get("avatar_url"),
            "projects_count": len(projects),
            "projects": projects,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        if item:
            item.name = f"Jira ({clean_project_key})"
            item.encrypted_credentials = encrypted_secret
            item.channel_or_project_id = clean_project_key
            item.status = "ACTIVE"
            item.metadata_json = meta
            item.updated_at = datetime.now(timezone.utc)
        else:
            item = Integration(
                tenant_id=tenant_id,
                provider="JIRA",
                name=f"Jira ({clean_project_key})",
                encrypted_credentials=encrypted_secret,
                channel_or_project_id=clean_project_key,
                events_subscribed=["ACTION_CREATED", "DECISION_CONFIRMED"],
                status="ACTIVE",
                metadata_json=meta,
            )
            db.add(item)

        # 5. Record Audit Event
        ev = IntegrationEvent(
            tenant_id=tenant_id,
            integration_id=item.id,
            direction="OUTBOUND",
            external_event_id=f"jira_conn_{uuid.uuid4().hex[:10]}",
            event_type="JIRA_CONNECTED",
            status="COMPLETED",
            payload_json={
                "instance_url": norm_url,
                "project_key": clean_project_key,
                "project_name": project_name,
                "user": profile.get("display_name"),
                "email": verified_email,
            },
            response_status_code=200,
        )
        db.add(ev)
        db.commit()
        db.refresh(item)

        return {
            "is_connected": True,
            "instance_url": norm_url,
            "project_key": clean_project_key,
            "project_name": project_name,
            "email": verified_email,
            "display_name": profile.get("display_name"),
            "projects": projects,
            "message": f"Successfully connected to Jira ({clean_project_key})!",
        }

    def get_credentials(self, tenant_id: uuid.UUID, db: Session) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt Jira credentials for tenant."""
        item = (
            db.query(Integration)
            .filter(Integration.tenant_id == tenant_id, Integration.provider == "JIRA")
            .first()
        )
        if not item or item.status != "ACTIVE" or not item.encrypted_credentials:
            return None

        try:
            raw = self.crypto.decrypt(item.encrypted_credentials)
            return json.loads(raw)
        except Exception as e:
            logger.error("Failed to decrypt Jira credentials: %s", str(e))
            return None

    def get_status(self, tenant_id: uuid.UUID, db: Session) -> Dict[str, Any]:
        """Return connectivity details for UI."""
        creds = self.get_credentials(tenant_id, db)
        if not creds:
            return {
                "is_connected": False,
                "instance_url": None,
                "email": None,
                "account_email": None,
                "project_key": None,
                "project_name": None,
                "display_name": None,
                "projects": [],
            }

        item = (
            db.query(Integration)
            .filter(Integration.tenant_id == tenant_id, Integration.provider == "JIRA")
            .first()
        )
        meta = item.metadata_json or {} if item else {}

        return {
            "is_connected": True,
            "instance_url": creds.get("instance_url"),
            "email": creds.get("email"),
            "account_email": creds.get("email"),
            "project_key": creds.get("project_key") or item.channel_or_project_id or "SCRUM",
            "project_name": meta.get("project_name") or f"Project {creds.get('project_key') or 'SCRUM'}",
            "display_name": meta.get("display_name") or creds.get("email"),
            "connected_at": meta.get("connected_at"),
            "last_synced_at": item.updated_at.isoformat() if item and item.updated_at else None,
            "projects": meta.get("projects") or [],
        }

    def fetch_issues(
        self,
        tenant_id: uuid.UUID,
        db: Session,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch latest sprint issues from connected Jira project using /rest/api/3/search/jql."""
        creds = self.get_credentials(tenant_id, db)
        if not creds:
            return []

        norm_url = creds["instance_url"]
        project_key = creds.get("project_key") or "SCRUM"
        token = creds.get("api_token", "")

        if not token or token.startswith("demo_") or token == "jira_demo_token_knowra_live":
            return []

        auth_header = self.get_auth_header(creds["email"], creds["api_token"])

        # Note: Atlassian removed /rest/api/3/search (HTTP 410) and requires /rest/api/3/search/jql
        endpoint = f"{norm_url}/rest/api/3/search/jql"
        payload = {
            "jql": f"project = {project_key} ORDER BY created DESC",
            "maxResults": max(1, min(50, max_results)),
            "fields": ["summary", "status", "priority", "assignee", "created", "issuetype"],
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Knowra-Intelligence/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
                issues = data.get("issues", [])
                
                parsed_issues = []
                for iss in issues:
                    fields = iss.get("fields") or {}
                    status_obj = fields.get("status") or {}
                    priority_obj = fields.get("priority") or {}
                    assignee_obj = fields.get("assignee") or {}
                    issuetype_obj = fields.get("issuetype") or {}

                    parsed_issues.append({
                        "id": iss.get("id"),
                        "key": iss.get("key"),
                        "summary": fields.get("summary") or "Untitled Issue",
                        "status": status_obj.get("name") or "To Do",
                        "priority": priority_obj.get("name") or "Medium",
                        "assignee": assignee_obj.get("displayName") or "Unassigned",
                        "issue_type": issuetype_obj.get("name") or "Task",
                        "created": fields.get("created"),
                        "url": f"{norm_url}/browse/{iss.get('key')}",
                    })
                return parsed_issues
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning("Could not fetch Jira issues HTTP %d: %s", e.code, err_body[:200])
            return []
        except Exception as e:
            logger.warning("Could not fetch Jira issues: %s", str(e))
            return []

    def create_issue(
        self,
        tenant_id: uuid.UUID,
        summary: str,
        description: str,
        db: Session,
        issue_type: str = "Task",
        priority: str = "Medium",
        project_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a real Jira ticket from a meeting action item with resilient payload handling."""
        creds = self.get_credentials(tenant_id, db)
        if not creds:
            raise ValueError("Jira is not connected for this workspace.")

        norm_url = creds["instance_url"]
        active_project_key = (project_key or creds.get("project_key") or "SCRUM").strip().upper()
        token = creds.get("api_token", "")

        if not token or token.startswith("demo_") or token == "jira_demo_token_knowra_live":
            raise ValueError(
                "A real Atlassian API Token is required to create tickets in Jira. "
                "Please configure JIRA_API_TOKEN in your .env file."
            )

        auth_header = self.get_auth_header(creds["email"], creds["api_token"])
        endpoint = f"{norm_url}/rest/api/3/issue"

        # Atlassian Document Format (ADF) description for v3 API
        adf_desc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": description or "Action item created automatically by Knowra AI Assistant.",
                        }
                    ],
                }
            ],
        }

        # Attempt 1: Standard payload including priority
        payload_with_priority = {
            "fields": {
                "project": {"key": active_project_key},
                "summary": summary,
                "description": adf_desc,
                "issuetype": {"name": issue_type or "Task"},
                "priority": {"name": priority or "Medium"},
            }
        }

        # Attempt 2: Minimal fallback without priority in case project schema omits it
        payload_without_priority = {
            "fields": {
                "project": {"key": active_project_key},
                "summary": summary,
                "description": adf_desc,
                "issuetype": {"name": issue_type or "Task"},
            }
        }

        last_error = None
        for payload in (payload_with_priority, payload_without_priority):
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=data_bytes,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Knowra-Intelligence/1.0",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    created_key = res_data.get("key")
                    issue_id = res_data.get("id")
                    issue_url = f"{norm_url}/browse/{created_key}"

                    # Record outbound integration event
                    item = (
                        db.query(Integration)
                        .filter(Integration.tenant_id == tenant_id, Integration.provider == "JIRA")
                        .first()
                    )
                    ev = IntegrationEvent(
                        tenant_id=tenant_id,
                        integration_id=item.id if item else None,
                        direction="OUTBOUND",
                        external_event_id=f"jira_{created_key}",
                        event_type="ACTION_CREATED",
                        status="COMPLETED",
                        payload_json={
                            "issue_key": created_key,
                            "summary": summary,
                            "url": issue_url,
                            "project_key": active_project_key,
                        },
                        response_status_code=201,
                    )
                    db.add(ev)
                    db.commit()

                    return {
                        "success": True,
                        "key": created_key,
                        "id": issue_id,
                        "url": issue_url,
                        "summary": summary,
                    }
            except urllib.error.HTTPError as e:
                last_error = e
                err_body = e.read().decode("utf-8", errors="replace")
                logger.warning("Jira issue creation attempt failed HTTP %d: %s", e.code, err_body[:200])
                # If 400 relates to priority field, retry with second payload
                if e.code == 400 and ("priority" in err_body.lower() or "field" in err_body.lower()):
                    continue
                raise ValueError(f"Failed to create Jira issue ({e.code}): {err_body[:200]}")
            except Exception as e:
                last_error = e
                logger.exception("Unexpected error creating Jira issue")
                break

        raise ValueError(f"Could not create issue in Jira: {str(last_error or 'Unknown error')}")

    def disconnect(self, tenant_id: Any, db: Session) -> bool:
        """Disconnect and revoke Jira integration for tenant."""
        tid = str(tenant_id)
        items = (
            db.query(Integration)
            .filter(Integration.provider == "JIRA")
            .all()
        )
        matched = [i for i in items if str(i.tenant_id) == tid or i.tenant_id == tenant_id]
        if matched:
            for item in matched:
                item.status = "INACTIVE"
            db.commit()
            return True
        return False


jira_service = JiraIntegrationService()
