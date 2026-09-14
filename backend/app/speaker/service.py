"""
Phase 14 – Speaker Identity Service

Orchestrates the full identity resolution workflow:

  1. Candidate generation  – query voice-matching engine with tenant-scoped profiles.
  2. Suggestion creation   – persist a SUGGESTED SpeakerIdentityAssignment.
  3. Confirmation/Rejection – human operator confirms or rejects via the API.
  4. History logging        – every status transition is appended to SpeakerIdentityHistory.
  5. Audit event emission   – SPEAKER_IDENTITY_CONFIRMED logged to audit_logs.

Tenant isolation
----------------
All DB queries use an explicit tenant_id equality filter.  The service NEVER
reads SpeakerProfile rows from a different tenant, even in candidate generation.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from sqlalchemy.orm import Session, selectinload

from app.models.audit_log import AuditLog
from app.models.speaker import Speaker
from app.models.speaker_identity import (
    SpeakerIdentityAssignment,
    SpeakerIdentityHistory,
    SpeakerProfile,
)
from app.speaker.matching import EmbeddingProfile, VoiceMatchingEngine, VoiceMatchConfig
from app.speaker.schemas import (
    IdentityCandidate,
    IdentityCandidatesResponse,
    IdentityAssignmentResponse,
    IdentityHistoryResponse,
    IdentityHistoryEntry,
    SpeakerProfileCreateRequest,
    SpeakerProfileResponse,
)

logger = structlog.get_logger(__name__)


class IdentityNotFoundError(Exception):
    pass


class IdentityViolationError(Exception):
    """Raised when a requested action would violate segregation invariants."""


class SpeakerIdentityService:
    def __init__(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        match_config: Optional[VoiceMatchConfig] = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self._engine = VoiceMatchingEngine(match_config)

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        request: SpeakerProfileCreateRequest,
    ) -> SpeakerProfileResponse:
        """Create a new SpeakerProfile within the caller's tenant."""
        profile = SpeakerProfile(
            tenant_id=self.tenant_id,
            user_id=request.user_id,
            display_name=request.display_name,
            participant_type=request.participant_type,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return SpeakerProfileResponse.model_validate(profile)

    def get_profile(self, profile_id: uuid.UUID) -> SpeakerProfileResponse:
        profile = self._fetch_profile(profile_id)
        return SpeakerProfileResponse.model_validate(profile)

    # ------------------------------------------------------------------
    # Candidate generation (Phase 14 core)
    # ------------------------------------------------------------------

    def get_identity_candidates(
        self,
        meeting_id: uuid.UUID,
        speaker_id: uuid.UUID,
        query_embedding: Optional[List[float]] = None,
    ) -> IdentityCandidatesResponse:
        """
        Return ranked identity candidates for a diarization speaker cluster.

        Security invariant: only SpeakerProfile rows whose tenant_id equals
        self.tenant_id are evaluated.  This is enforced at the DB query level,
        not merely at the application level.
        """
        speaker = self._fetch_speaker(meeting_id, speaker_id)

        # Load ALL tenant-scoped profiles that have a stored embedding.
        # Cross-tenant profiles are excluded by the tenant_id filter below.
        tenant_profiles_db: List[SpeakerProfile] = (
            self.db.query(SpeakerProfile)
            .filter(
                SpeakerProfile.tenant_id == self.tenant_id,
                SpeakerProfile.embedding_json.isnot(None),
            )
            .all()
        )

        embedding_profiles = [
            EmbeddingProfile(
                speaker_profile_id=p.id,
                display_name=p.display_name,
                participant_type=p.participant_type,
                user_id=p.user_id,
                embedding=p.embedding_json or [],
            )
            for p in tenant_profiles_db
        ]

        candidates = self._engine.find_candidates(
            query_embedding=query_embedding or [],
            tenant_profiles=embedding_profiles,
            speaker_id=speaker.id,
            speaker_label=speaker.speaker_label,
        )

        return IdentityCandidatesResponse(
            speaker_id=speaker.id,
            speaker_label=speaker.speaker_label,
            candidates=candidates,
        )

    # ------------------------------------------------------------------
    # Suggestion persistence
    # ------------------------------------------------------------------

    def create_suggestion(
        self,
        speaker_id: uuid.UUID,
        speaker_profile_id: uuid.UUID,
        similarity_score: float,
    ) -> IdentityAssignmentResponse:
        """
        Persist a SUGGESTED identity assignment produced by the matching engine.
        One active assignment per speaker is enforced; a new suggestion supersedes
        any existing SUGGESTED assignment for the same speaker.
        """
        self._fetch_profile(speaker_profile_id)  # validates tenant ownership

        # Supersede any existing SUGGESTED assignment
        existing = (
            self.db.query(SpeakerIdentityAssignment)
            .filter(
                SpeakerIdentityAssignment.speaker_id == speaker_id,
                SpeakerIdentityAssignment.tenant_id == self.tenant_id,
                SpeakerIdentityAssignment.verification_status == "SUGGESTED",
            )
            .first()
        )
        if existing:
            self.db.delete(existing)
            self.db.flush()

        assignment = SpeakerIdentityAssignment(
            tenant_id=self.tenant_id,
            speaker_id=speaker_id,
            speaker_profile_id=speaker_profile_id,
            assignment_method="VOICE_MATCH",
            verification_status="SUGGESTED",
            similarity_score=similarity_score,
        )
        self.db.add(assignment)
        self.db.flush()

        self._append_history(
            assignment_id=assignment.id,
            status="SUGGESTED",
            event_name="SPEAKER_IDENTITY_SUGGESTED",
            actor_user_id=None,
            metadata={"similarity_score": similarity_score},
        )
        self.db.commit()
        self.db.refresh(assignment)
        return IdentityAssignmentResponse.model_validate(assignment)

    # ------------------------------------------------------------------
    # Human confirmation / rejection
    # ------------------------------------------------------------------

    def confirm_identity(
        self,
        meeting_id: uuid.UUID,
        speaker_id: uuid.UUID,
        speaker_profile_id: uuid.UUID,
        action: str,
        actor_user_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> IdentityAssignmentResponse:
        """
        Confirm or reject an identity suggestion.

        - On CONFIRMED: update assignment, append history, emit audit log entry.
        - On REJECTED: update assignment status only; no user_id linkage is made.

        Raises IdentityViolationError if attempting to link without CONFIRMED action.
        """
        if action not in ("CONFIRMED", "REJECTED"):
            raise IdentityViolationError(
                f"Invalid action '{action}'. Must be CONFIRMED or REJECTED."
            )

        self._fetch_speaker(meeting_id, speaker_id)
        self._fetch_profile(speaker_profile_id)  # validates tenant ownership

        # Find or create the assignment
        assignment = (
            self.db.query(SpeakerIdentityAssignment)
            .filter(
                SpeakerIdentityAssignment.speaker_id == speaker_id,
                SpeakerIdentityAssignment.speaker_profile_id == speaker_profile_id,
                SpeakerIdentityAssignment.tenant_id == self.tenant_id,
            )
            .first()
        )

        if not assignment:
            # Human is confirming manually (without a prior VOICE_MATCH suggestion)
            assignment = SpeakerIdentityAssignment(
                tenant_id=self.tenant_id,
                speaker_id=speaker_id,
                speaker_profile_id=speaker_profile_id,
                assignment_method="MANUAL",
                verification_status="SUGGESTED",
            )
            self.db.add(assignment)
            self.db.flush()

        assignment.verification_status = action
        assignment.actioned_by_user_id = actor_user_id

        event_name = (
            "SPEAKER_IDENTITY_CONFIRMED"
            if action == "CONFIRMED"
            else "SPEAKER_IDENTITY_REJECTED"
        )

        self._append_history(
            assignment_id=assignment.id,
            status=action,
            event_name=event_name,
            actor_user_id=actor_user_id,
            metadata={"note": note} if note else None,
        )

        if action == "CONFIRMED":
            # Emit structured audit log entry
            self._emit_audit_log(
                event_name=event_name,
                actor_user_id=actor_user_id,
                resource_id=str(assignment.id),
                metadata={
                    "speaker_id": str(speaker_id),
                    "speaker_profile_id": str(speaker_profile_id),
                    "note": note,
                },
            )

        self.db.commit()
        self.db.refresh(assignment)
        logger.info(
            "Identity assignment updated",
            action=action,
            speaker_id=str(speaker_id),
            profile_id=str(speaker_profile_id),
            actor=str(actor_user_id),
        )
        return IdentityAssignmentResponse.model_validate(assignment)

    # ------------------------------------------------------------------
    # History retrieval
    # ------------------------------------------------------------------

    def get_identity_history(
        self,
        meeting_id: uuid.UUID,
        speaker_id: uuid.UUID,
    ) -> IdentityHistoryResponse:
        self._fetch_speaker(meeting_id, speaker_id)

        assignments = (
            self.db.query(SpeakerIdentityAssignment)
            .options(
                selectinload(SpeakerIdentityAssignment.history)
            )
            .filter(
                SpeakerIdentityAssignment.speaker_id == speaker_id,
                SpeakerIdentityAssignment.tenant_id == self.tenant_id,
            )
            .all()
        )

        if not assignments:
            return IdentityHistoryResponse(
                assignment_id=uuid.uuid4(),
                speaker_id=speaker_id,
                history=[],
            )

        all_history = []
        for a in assignments:
            all_history.extend(a.history)

        all_history.sort(key=lambda h: h.created_at)

        history_entries = [
            IdentityHistoryEntry(
                id=h.id,
                status=h.status,
                event_name=h.event_name,
                actor_user_id=h.actor_user_id,
                metadata_json=h.metadata_json,
                created_at=h.created_at,
            )
            for h in all_history
        ]

        latest_assignment = max(assignments, key=lambda a: a.updated_at or a.created_at)

        return IdentityHistoryResponse(
            assignment_id=latest_assignment.id,
            speaker_id=speaker_id,
            history=history_entries,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_speaker(self, meeting_id: uuid.UUID, speaker_id: uuid.UUID) -> Speaker:
        speaker = (
            self.db.query(Speaker)
            .filter(
                Speaker.id == speaker_id,
                Speaker.meeting_id == meeting_id,
                Speaker.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not speaker:
            raise IdentityNotFoundError(
                f"Speaker {speaker_id} not found in meeting {meeting_id} "
                f"for tenant {self.tenant_id}"
            )
        return speaker

    def _fetch_profile(self, profile_id: uuid.UUID) -> SpeakerProfile:
        """
        Fetch a SpeakerProfile, enforcing tenant ownership.

        The tenant_id filter here is the hard security boundary:
        a profile from another tenant will raise IdentityNotFoundError
        rather than returning data.
        """
        profile = (
            self.db.query(SpeakerProfile)
            .filter(
                SpeakerProfile.id == profile_id,
                SpeakerProfile.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not profile:
            raise IdentityNotFoundError(
                f"SpeakerProfile {profile_id} not found for tenant {self.tenant_id}"
            )
        return profile

    def _append_history(
        self,
        assignment_id: uuid.UUID,
        status: str,
        event_name: str,
        actor_user_id: Optional[uuid.UUID],
        metadata: Optional[dict] = None,
    ) -> None:
        history = SpeakerIdentityHistory(
            tenant_id=self.tenant_id,
            assignment_id=assignment_id,
            status=status,
            event_name=event_name,
            actor_user_id=actor_user_id,
            metadata_json=metadata,
        )
        self.db.add(history)
        self.db.flush()

    def _emit_audit_log(
        self,
        event_name: str,
        actor_user_id: uuid.UUID,
        resource_id: str,
        metadata: Optional[dict] = None,
    ) -> None:
        entry = AuditLog(
            organization_id=self.tenant_id,
            user_id=actor_user_id,
            action=event_name,
            resource_type="SpeakerIdentityAssignment",
            resource_id=resource_id,
            success=True,
            metadata_json=metadata,
        )
        self.db.add(entry)
        self.db.flush()
