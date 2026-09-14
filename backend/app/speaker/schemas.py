"""
Phase 14 – Speaker Identity Schemas (Pydantic v2)

Covers all payloads for:
  - SpeakerProfile CRUD
  - Candidate suggestion responses
  - Identity confirmation/rejection requests
  - Full history trail responses
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Participant type literal
# ---------------------------------------------------------------------------

ParticipantType = Literal["INTERNAL_USER", "EXTERNAL_PARTICIPANT", "UNKNOWN"]
VerificationStatus = Literal["SUGGESTED", "CONFIRMED", "REJECTED"]
AssignmentMethod = Literal["VOICE_MATCH", "MANUAL", "SYSTEM"]


# ---------------------------------------------------------------------------
# SpeakerProfile
# ---------------------------------------------------------------------------

class SpeakerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID]
    display_name: str
    participant_type: ParticipantType
    embedding_model: Optional[str]
    created_at: datetime
    updated_at: datetime


class SpeakerProfileCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    participant_type: ParticipantType = "UNKNOWN"
    # Provide user_id only for INTERNAL_USER – the server validates FK existence.
    user_id: Optional[UUID] = None


# ---------------------------------------------------------------------------
# Identity candidate (returned by the matching engine)
# ---------------------------------------------------------------------------

class IdentityCandidate(BaseModel):
    """A single match candidate returned by the voice-matching engine."""
    speaker_profile_id: UUID
    display_name: str
    participant_type: ParticipantType
    # Cosine similarity in [0.0, 1.0]; higher is more likely a match.
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    # The linked internal user (only set for INTERNAL_USER profiles with a confirmed user_id)
    user_id: Optional[UUID] = None


class IdentityCandidatesResponse(BaseModel):
    speaker_id: UUID
    speaker_label: str
    candidates: List[IdentityCandidate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Identity confirmation/rejection request
# ---------------------------------------------------------------------------

class IdentityConfirmRequest(BaseModel):
    """
    Submitted by a human operator to confirm or reject a candidate suggestion.

    Confirming an identity assignment with status CONFIRMED logs the
    SPEAKER_IDENTITY_CONFIRMED audit event.

    Rejecting sets verification_status = REJECTED and appends a
    SPEAKER_IDENTITY_REJECTED history row.
    """
    speaker_profile_id: UUID
    action: VerificationStatus = Field(
        ...,
        description="Must be CONFIRMED or REJECTED (not SUGGESTED)",
    )
    # Free-text note for the audit record
    note: Optional[str] = Field(None, max_length=512)

    def model_post_init(self, __context) -> None:
        if self.action == "SUGGESTED":
            raise ValueError(
                "action must be CONFIRMED or REJECTED, not SUGGESTED"
            )


class IdentityAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    speaker_id: UUID
    speaker_profile_id: UUID
    assignment_method: AssignmentMethod
    verification_status: VerificationStatus
    similarity_score: Optional[float]
    actioned_by_user_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# History trail
# ---------------------------------------------------------------------------

class IdentityHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    event_name: str
    actor_user_id: Optional[UUID]
    metadata_json: Optional[dict]
    created_at: datetime


class IdentityHistoryResponse(BaseModel):
    assignment_id: UUID
    speaker_id: UUID
    history: List[IdentityHistoryEntry] = Field(default_factory=list)
