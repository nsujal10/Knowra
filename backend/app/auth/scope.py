"""
Phase 21 – Authorized Retrieval Scope

Encapsulates user authentication, tenant boundaries, RBAC permissions,
and resource-level access constraints strictly decoupled from vector/storage engines.
"""

from __future__ import annotations

from typing import Collection, Optional, Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthorizedRetrievalScope(BaseModel):
    """
    Carries verified security invariants into the retrieval pipeline.

    Invariants:
      1. Retrieval is strictly isolated to `tenant_id` at the SQL predicate level.
      2. If `allowed_meeting_ids` is None, the principal possesses tenant-wide meeting read access.
      3. If `allowed_meeting_ids` is a set, retrieval is restricted strictly to meetings in that set.
      4. If `allowed_meeting_ids` is empty, the principal has 0 accessible meetings (empty retrieval).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tenant_id: UUID
    user_id: UUID
    role_code: str
    permissions: Set[str] = Field(default_factory=set)
    allowed_meeting_ids: Optional[Set[UUID]] = None

    def has_permission(self, permission_code: str) -> bool:
        """Verify if the current scope includes a specific permission."""
        return permission_code in self.permissions

    def can_access_meeting(self, meeting_id: UUID) -> bool:
        """Determines if the principal has access to a specific meeting ID."""
        if self.allowed_meeting_ids is None:
            return True
        return meeting_id in self.allowed_meeting_ids

    def get_effective_meeting_filter(
        self, requested_meeting_id: Optional[UUID] = None
    ) -> Optional[Set[UUID]]:
        """
        Resolves the exact set of meeting UUIDs to filter in SQL queries.

        - If requested_meeting_id is provided and allowed, returns {requested_meeting_id}.
        - If requested_meeting_id is provided but not allowed, returns an empty set (0 hits).
        - If no requested_meeting_id, returns self.allowed_meeting_ids (None or subset).
        """
        if requested_meeting_id is not None:
            if self.can_access_meeting(requested_meeting_id):
                return {requested_meeting_id}
            # Access explicitly forbidden
            return set()
        return self.allowed_meeting_ids
