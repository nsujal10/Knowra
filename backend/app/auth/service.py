"""
Phase 21 – Authorization Service

Enforces resource-level RBAC and tenant boundaries for RAG retrieval and citation access.
Completely decoupled from vector stores and LLM logic.
"""

from __future__ import annotations

from typing import Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.scope import AuthorizedRetrievalScope
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.schemas.auth import CurrentUserContext
from app.security.exceptions import ForbiddenException


class AuthorizationService:
    """
    Evaluates enterprise access control policies, tenant boundaries,
    and resource-level visibility to generate an AuthorizedRetrievalScope.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_scope(
        self,
        current_user: CurrentUserContext,
        requested_meeting_id: Optional[UUID] = None,
    ) -> AuthorizedRetrievalScope:
        """
        Derives the AuthorizedRetrievalScope from current user context and database RBAC policies.

        - Enforces strict tenant separation.
        - ADMIN and MANAGER roles have tenant-wide visibility across all tenant meetings.
        - Other roles have access restricted to meetings they own or are assigned to.
        - If requested_meeting_id is provided, validates that it exists in the tenant and is accessible.
        """
        tenant_id = current_user.organization_id
        user_id = current_user.user_id
        role_code = (current_user.role_code or "").upper()
        permissions = set(current_user.permissions or [])

        # 1. Resolve meeting accessibility set
        allowed_meeting_ids: Optional[Set[UUID]] = None

        if role_code in ("ADMIN", "MANAGER") or "meetings:read_all" in permissions:
            # Tenant-wide meeting access
            allowed_meeting_ids = None
        else:
            # Scoped access: meetings owned by this user within this tenant
            meetings = (
                self.db.query(Meeting.id)
                .filter(
                    Meeting.tenant_id == tenant_id,
                    Meeting.owner_id == user_id,
                )
                .all()
            )
            allowed_meeting_ids = {m.id for m in meetings}

        # 2. If a specific meeting is requested, check access upfront
        if requested_meeting_id is not None:
            # Verify meeting exists in this tenant
            target_meeting = (
                self.db.query(Meeting)
                .filter(
                    Meeting.id == requested_meeting_id,
                    Meeting.tenant_id == tenant_id,
                )
                .first()
            )
            if not target_meeting:
                raise ForbiddenException("Requested meeting not found or cross-tenant access denied.")

            if allowed_meeting_ids is not None and requested_meeting_id not in allowed_meeting_ids:
                raise ForbiddenException("User does not have permission to access the requested meeting.")

        return AuthorizedRetrievalScope(
            tenant_id=tenant_id,
            user_id=user_id,
            role_code=role_code,
            permissions=permissions,
            allowed_meeting_ids=allowed_meeting_ids,
        )

    def validate_citation_access(
        self,
        scope: AuthorizedRetrievalScope,
        segment_id: UUID,
    ) -> bool:
        """
        Guarantees Citation IDOR Defense:
        Cross-references a transcript segment to its parent meeting and confirms
        that the authenticated scope holds permission to view that meeting.
        """
        # Fetch segment within tenant boundary
        segment = (
            self.db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.id == segment_id,
                TranscriptSegment.tenant_id == scope.tenant_id,
            )
            .first()
        )
        if not segment:
            return False

        # Resolve parent meeting via transcript
        transcript = (
            self.db.query(Transcript)
            .filter(
                Transcript.id == segment.transcript_id,
                Transcript.tenant_id == scope.tenant_id,
            )
            .first()
        )
        if not transcript:
            return False

        return scope.can_access_meeting(transcript.meeting_id)

    def can_access_meeting(
        self,
        scope: AuthorizedRetrievalScope,
        meeting_id: UUID,
    ) -> bool:
        """Checks whether the scope permits access to the given meeting."""
        meeting = (
            self.db.query(Meeting.id)
            .filter(
                Meeting.id == meeting_id,
                Meeting.tenant_id == scope.tenant_id,
            )
            .first()
        )
        if not meeting:
            return False
        return scope.can_access_meeting(meeting_id)
