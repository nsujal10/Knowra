"""
Phase 14 – Speaker Identity API Endpoints

GET  /meetings/{meeting_id}/speakers/{speaker_id}/candidates
     Returns voice-match candidate suggestions scoped strictly to the caller's tenant.

POST /meetings/{meeting_id}/speakers/{speaker_id}/identity
     Human operator confirms or rejects a candidate. Logs SPEAKER_IDENTITY_CONFIRMED
     or SPEAKER_IDENTITY_REJECTED audit event.

GET  /meetings/{meeting_id}/speakers/{speaker_id}/identity/history
     Returns the full audit history trail for a speaker's identity assignment.

POST /speaker-profiles
     Create a reusable SpeakerProfile within the caller's tenant.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.tenant_db import get_tenant_db
from app.security.tenant import TenantContext, get_tenant_context
from app.speaker.schemas import (
    IdentityCandidatesResponse,
    IdentityAssignmentResponse,
    IdentityConfirmRequest,
    IdentityHistoryResponse,
    SpeakerProfileCreateRequest,
    SpeakerProfileResponse,
)
from app.speaker.service import (
    SpeakerIdentityService,
    IdentityNotFoundError,
    IdentityViolationError,
)

router = APIRouter()


def _get_service(
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> SpeakerIdentityService:
    return SpeakerIdentityService(db=db, tenant_id=tenant_ctx.tenant_id)


# ---------------------------------------------------------------------------
# Speaker Profile endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/speaker-profiles",
    response_model=SpeakerProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a speaker profile",
    tags=["Speaker Identity"],
)
def create_speaker_profile(
    request: SpeakerProfileCreateRequest,
    service: SpeakerIdentityService = Depends(_get_service),
) -> SpeakerProfileResponse:
    """
    Create a reusable SpeakerProfile for a recurring participant.
    The profile is strictly scoped to the caller's tenant.
    """
    return service.create_profile(request)


@router.get(
    "/speaker-profiles/{profile_id}",
    response_model=SpeakerProfileResponse,
    summary="Get a speaker profile",
    tags=["Speaker Identity"],
)
def get_speaker_profile(
    profile_id: UUID,
    service: SpeakerIdentityService = Depends(_get_service),
) -> SpeakerProfileResponse:
    try:
        return service.get_profile(profile_id)
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

@router.get(
    "/meetings/{meeting_id}/speakers/{speaker_id}/candidates",
    response_model=IdentityCandidatesResponse,
    summary="Get identity match candidates for a speaker",
    tags=["Speaker Identity"],
)
def get_identity_candidates(
    meeting_id: UUID,
    speaker_id: UUID,
    service: SpeakerIdentityService = Depends(_get_service),
) -> IdentityCandidatesResponse:
    """
    Return voice-match candidates for an unidentified diarization speaker.

    Candidates are drawn EXCLUSIVELY from SpeakerProfiles within the caller's
    tenant.  Cross-tenant candidate generation is strictly prohibited.

    Note: voice embeddings are required in speaker profiles for non-empty results.
    Profiles without embeddings are automatically excluded from the candidate set.
    """
    try:
        return service.get_identity_candidates(
            meeting_id=meeting_id,
            speaker_id=speaker_id,
        )
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# Human confirmation / rejection
# ---------------------------------------------------------------------------

@router.post(
    "/meetings/{meeting_id}/speakers/{speaker_id}/identity",
    response_model=IdentityAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or reject a speaker identity",
    tags=["Speaker Identity"],
)
def confirm_speaker_identity(
    meeting_id: UUID,
    speaker_id: UUID,
    request: IdentityConfirmRequest,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> IdentityAssignmentResponse:
    """
    Confirm or reject an identity match.

    - `action: CONFIRMED` → writes SPEAKER_IDENTITY_CONFIRMED audit event.
    - `action: REJECTED`  → writes SPEAKER_IDENTITY_REJECTED history entry.

    The assignment is NEVER automatically CONFIRMED; human action is always required.
    """
    service = SpeakerIdentityService(db=db, tenant_id=tenant_ctx.tenant_id)
    try:
        return service.confirm_identity(
            meeting_id=meeting_id,
            speaker_id=speaker_id,
            speaker_profile_id=request.speaker_profile_id,
            action=request.action,
            actor_user_id=tenant_ctx.user_id,
            note=request.note,
        )
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IdentityViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


# ---------------------------------------------------------------------------
# History trail
# ---------------------------------------------------------------------------

@router.get(
    "/meetings/{meeting_id}/speakers/{speaker_id}/identity/history",
    response_model=IdentityHistoryResponse,
    summary="Get speaker identity assignment history",
    tags=["Speaker Identity"],
)
def get_identity_history(
    meeting_id: UUID,
    speaker_id: UUID,
    service: SpeakerIdentityService = Depends(_get_service),
) -> IdentityHistoryResponse:
    """
    Return the complete, immutable audit trail of identity transitions
    for a diarization speaker cluster.
    """
    try:
        return service.get_identity_history(
            meeting_id=meeting_id,
            speaker_id=speaker_id,
        )
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
