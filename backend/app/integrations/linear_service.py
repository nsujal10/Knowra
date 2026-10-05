"""
Linear GraphQL API Integration Service

Handles:
  - Linear GraphQL API client authentication (Personal API Keys & OAuth)
  - Profile & team verification via Linear GraphQL viewer query
  - Live Linear issue retrieval
  - Direct issue creation from meeting action items
  - AES-256 encrypted credential persistence
"""

import json
import logging
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.integrations.crypto import SecretEncryptionService
from app.integrations.models import Integration, IntegrationEvent

logger = logging.getLogger(__name__)

LINEAR_GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"


class LinearIntegrationService:
    def __init__(self):
        self.crypto = SecretEncryptionService()

    def _execute_graphql(self, api_key: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query or mutation against Linear's API."""
        clean_key = (api_key or "").strip()
        if not clean_key:
            raise ValueError("Linear API Key is required.")

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            LINEAR_GRAPHQL_ENDPOINT,
            data=data_bytes,
            headers={
                "Authorization": clean_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Knowra-Intelligence/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                if "errors" in result and result["errors"]:
                    err_msg = result["errors"][0].get("message", "Linear GraphQL error")
                    logger.error("Linear GraphQL error: %s", err_msg)
                    raise ValueError(f"Linear API error: {err_msg}")
                return result.get("data", {})
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("Linear API HTTP error %d: %s", e.code, err_body)
            if e.code in (401, 403):
                raise ValueError("Authentication failed. Please verify your Linear API Key.")
            raise ValueError(f"Linear API HTTP error ({e.code}): {err_body[:200]}")
        except urllib.error.URLError as e:
            logger.error("Linear network error: %s", e.reason)
            raise ValueError("Could not connect to Linear API. Please check your internet connection.")
        except Exception as e:
            logger.exception("Unexpected error communicating with Linear")
            raise ValueError(f"Failed to communicate with Linear: {str(e)}")

    def verify_credentials(self, api_key: str) -> Dict[str, Any]:
        """Verify Linear credentials by querying viewer and accessible teams."""
        query = """
        query {
          viewer {
            id
            name
            email
            admin
            organization {
              id
              name
              urlKey
            }
          }
          teams {
            nodes {
              id
              name
              key
            }
          }
        }
        """
        data = self._execute_graphql(api_key, query)
        viewer = data.get("viewer") or {}
        teams = (data.get("teams") or {}).get("nodes", [])

        return {
            "valid": True,
            "viewer_id": viewer.get("id"),
            "name": viewer.get("name") or "Linear User",
            "email": viewer.get("email") or "",
            "organization": (viewer.get("organization") or {}).get("name", "Linear Workspace"),
            "org_key": (viewer.get("organization") or {}).get("urlKey", ""),
            "teams": teams,
        }

    def save_connection(
        self,
        tenant_id: uuid.UUID,
        api_key: str,
        team_key: str,
        db: Session,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify, encrypt, and persist Linear credentials."""
        profile = self.verify_credentials(api_key)
        teams = profile.get("teams", [])

        target_team = None
        if team_key:
            target_team = next((t for t in teams if t["key"].upper() == team_key.upper()), None)
        if not target_team and teams:
            target_team = teams[0]

        resolved_team_key = target_team["key"] if target_team else (team_key or "ENG").upper()
        resolved_team_id = target_team["id"] if target_team else None
        resolved_team_name = target_team["name"] if target_team else resolved_team_key

        secret_payload = {
            "api_key": api_key.strip(),
            "team_key": resolved_team_key,
            "team_id": resolved_team_id,
            "organization": profile.get("organization"),
            "email": email or profile.get("email"),
        }
        encrypted_secret = self.crypto.encrypt(json.dumps(secret_payload))

        tid = str(tenant_id)
        items = db.query(Integration).filter(Integration.provider == "LINEAR").all()
        matched = [i for i in items if str(i.tenant_id) == tid or i.tenant_id == tenant_id]

        meta = {
            "team_key": resolved_team_key,
            "team_id": resolved_team_id,
            "team_name": resolved_team_name,
            "viewer_name": profile.get("name"),
            "viewer_email": email or profile.get("email"),
            "organization": profile.get("organization"),
            "teams_count": len(teams),
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        if matched:
            item = matched[0]
            item.name = f"Linear ({resolved_team_key})"
            item.encrypted_credentials = encrypted_secret
            item.channel_or_project_id = resolved_team_key
            item.status = "ACTIVE"
            item.metadata_json = meta
            item.updated_at = datetime.now(timezone.utc)
        else:
            item = Integration(
                tenant_id=tenant_id,
                provider="LINEAR",
                name=f"Linear ({resolved_team_key})",
                encrypted_credentials=encrypted_secret,
                channel_or_project_id=resolved_team_key,
                events_subscribed=["ACTION_CREATED", "DECISION_CONFIRMED"],
                status="ACTIVE",
                metadata_json=meta,
            )
            db.add(item)

        db.commit()

        # Audit event
        ev = IntegrationEvent(
            tenant_id=tenant_id,
            integration_id=item.id,
            direction="OUTBOUND",
            external_event_id=f"linear_conn_{uuid.uuid4().hex[:10]}",
            event_type="LINEAR_CONNECTED",
            status="COMPLETED",
            payload_json={
                "team_key": resolved_team_key,
                "organization": profile.get("organization"),
                "user": profile.get("name"),
            },
            response_status_code=200,
        )
        db.add(ev)
        db.commit()

        return {
            "success": True,
            "message": f"Successfully connected to Linear workspace ({profile.get('organization')}) for team {resolved_team_key}!",
            "team_key": resolved_team_key,
            "organization": profile.get("organization"),
            "viewer": profile.get("name"),
        }

    def get_credentials(self, tenant_id: uuid.UUID, db: Session) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt stored Linear credentials."""
        tid = str(tenant_id)
        items = db.query(Integration).filter(Integration.provider == "LINEAR", Integration.status == "ACTIVE").all()
        matched = [i for i in items if str(i.tenant_id) == tid or i.tenant_id == tenant_id]
        if not matched or not matched[0].encrypted_credentials:
            return None

        try:
            raw_json = self.crypto.decrypt(matched[0].encrypted_credentials)
            return json.loads(raw_json)
        except Exception as e:
            logger.error("Failed to decrypt Linear credentials: %s", str(e))
            return None

    def get_status(self, tenant_id: uuid.UUID, db: Session) -> Dict[str, Any]:
        """Check whether Linear is actively connected for tenant."""
        tid = str(tenant_id)
        items = db.query(Integration).filter(Integration.provider == "LINEAR").all()
        matched = [i for i in items if str(i.tenant_id) == tid or i.tenant_id == tenant_id]

        if not matched or matched[0].status != "ACTIVE":
            return {"is_connected": False}

        item = matched[0]
        meta = item.metadata_json or {}
        return {
            "is_connected": True,
            "team_key": meta.get("team_key") or item.channel_or_project_id,
            "team_name": meta.get("team_name"),
            "viewer_name": meta.get("viewer_name"),
            "viewer_email": meta.get("viewer_email"),
            "organization": meta.get("organization"),
            "last_synced_at": item.updated_at.isoformat() if item.updated_at else None,
        }

    def fetch_teams(self, tenant_id: uuid.UUID, db: Session) -> List[Dict[str, Any]]:
        """Fetch accessible teams from Linear."""
        creds = self.get_credentials(tenant_id, db)
        if not creds:
            return []

        query = """
        query {
          teams {
            nodes {
              id
              name
              key
            }
          }
        }
        """
        try:
            data = self._execute_graphql(creds["api_key"], query)
            return (data.get("teams") or {}).get("nodes", [])
        except Exception as e:
            logger.warning("Could not fetch Linear teams: %s", str(e))
            return []

    def fetch_issues(self, tenant_id: uuid.UUID, db: Session, max_results: int = 20) -> List[Dict[str, Any]]:
        """Fetch latest active sprint issues from Linear GraphQL API."""
        creds = self.get_credentials(tenant_id, db)
        if not creds:
            return []

        query = """
        query GetIssues($first: Int) {
          issues(first: $first, orderBy: createdAt) {
            nodes {
              id
              identifier
              title
              description
              priority
              priorityLabel
              url
              createdAt
              state {
                id
                name
                type
                color
              }
              assignee {
                id
                name
                email
              }
              team {
                id
                key
                name
              }
            }
          }
        }
        """
        try:
            data = self._execute_graphql(creds["api_key"], query, {"first": max_results})
            nodes = (data.get("issues") or {}).get("nodes", [])

            formatted = []
            for iss in nodes:
                pval = int(iss.get("priority") or 0)
                plabel = iss.get("priorityLabel")
                if not plabel or plabel.lower() == "no priority" or pval > 0:
                    if pval == 1:
                        plabel = "Urgent"
                    elif pval == 2:
                        plabel = "High"
                    elif pval == 3:
                        plabel = "Medium"
                    elif pval == 4:
                        plabel = "Low"
                    elif pval == 0:
                        plabel = "No Priority"

                assignee_obj = iss.get("assignee") or {}
                team_obj = iss.get("team") or {}

                formatted.append({
                    "id": iss.get("id"),
                    "identifier": iss.get("identifier"),
                    "title": iss.get("title") or "Untitled Issue",
                    "status": (iss.get("state") or {}).get("name") or "Backlog",
                    "state_color": (iss.get("state") or {}).get("color") or "#5e6ad2",
                    "priority": pval,
                    "priority_value": pval,
                    "priority_label": plabel or "No Priority",
                    "assignee": assignee_obj.get("name") if assignee_obj else None,
                    "assignee_email": assignee_obj.get("email") if assignee_obj else None,
                    "created_at": iss.get("createdAt"),
                    "created": iss.get("createdAt"),
                    "url": iss.get("url") or f"https://linear.app/issue/{iss.get('identifier')}",
                    "team_key": team_obj.get("key") or creds.get("team_key", "ENG"),
                    "team_name": team_obj.get("name"),
                })
            return formatted
        except Exception as e:
            logger.warning("Could not fetch Linear issues: %s", str(e))
            return []

    def create_issue(
        self,
        tenant_id: uuid.UUID,
        title: str,
        description: str,
        db: Session,
        team_key: Optional[str] = None,
        priority: int = 2,
    ) -> Dict[str, Any]:
        """Create a real Linear issue from a meeting action item."""
        creds = self.get_credentials(tenant_id, db)
        if not creds:
            raise ValueError("Linear is not connected for this workspace.")

        api_key = creds["api_key"]
        target_team_id = None

        # Resolve team ID dynamically from desired team_key
        if team_key:
            teams = self.fetch_teams(tenant_id, db)
            found = next((t for t in teams if t["key"].upper() == team_key.upper()), None)
            if found:
                target_team_id = found["id"]

        if not target_team_id:
            target_team_id = creds.get("team_id")

        if not target_team_id:
            teams = self.fetch_teams(tenant_id, db)
            if teams:
                target_team_id = teams[0]["id"]
            else:
                raise ValueError("No accessible Linear teams found to create this issue.")

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
              url
              priority
              priorityLabel
              state {
                name
                color
              }
            }
          }
        }
        """

        variables = {
            "input": {
                "title": title.strip(),
                "description": description or "Created automatically from Knowra Meeting Intelligence.",
                "teamId": target_team_id,
                "priority": int(priority),
            }
        }

        data = self._execute_graphql(api_key, mutation, variables)
        issue_data = (data.get("issueCreate") or {}).get("issue") or {}

        created_identifier = issue_data.get("identifier")
        issue_id = issue_data.get("id")
        issue_url = issue_data.get("url")

        # Record outbound event
        tid = str(tenant_id)
        items = db.query(Integration).filter(Integration.provider == "LINEAR").all()
        matched = [i for i in items if str(i.tenant_id) == tid or i.tenant_id == tenant_id]

        ev = IntegrationEvent(
            tenant_id=tenant_id,
            integration_id=matched[0].id if matched else None,
            direction="OUTBOUND",
            external_event_id=f"linear_{created_identifier}",
            event_type="ACTION_CREATED",
            status="COMPLETED",
            payload_json={
                "identifier": created_identifier,
                "title": title,
                "url": issue_url,
            },
            response_status_code=201,
        )
        db.add(ev)
        db.commit()

        return {
            "success": True,
            "identifier": created_identifier,
            "id": issue_id,
            "url": issue_url,
            "title": title,
            "status": (issue_data.get("state") or {}).get("name") or "To Do",
            "priority": issue_data.get("priorityLabel") or "Medium",
        }

    def disconnect(self, tenant_id: Any, db: Session) -> bool:
        """Disconnect Linear integration for tenant."""
        tid = str(tenant_id)
        items = db.query(Integration).filter(Integration.provider == "LINEAR").all()
        matched = [i for i in items if str(i.tenant_id) == tid or i.tenant_id == tenant_id]

        if matched:
            for item in matched:
                item.status = "INACTIVE"
            db.commit()
            return True
        return False


linear_service = LinearIntegrationService()
