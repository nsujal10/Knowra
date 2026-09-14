"""
Phase 13 – Canonical Transcript API Endpoints

GET  /meetings/{meeting_id}/transcript
     Returns the canonical JSON for the latest version, or a specific version
     if ?version= is supplied.

POST /meetings/{meeting_id}/transcript/versions
     Submit a human edit; returns the new version number.

GET  /meetings/{meeting_id}/transcript/versions
     List all available version numbers and their metadata.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.tenant_db import get_tenant_db
from app.security.tenant import TenantContext, get_tenant_context
from app.transcript.schemas import (
    CanonicalTranscript,
    TranscriptEditRequest,
    TranscriptEditResponse,
    TranscriptVersionMeta,
)
from app.transcript.service import (
    CanonicalTranscriptService,
    TranscriptNotFoundError,
    TranscriptVersioningError,
)
from app.transcript.validator import SegmentValidationError
from app.models.transcript import Transcript
from app.models.transcript_version import TranscriptVersion

router = APIRouter()


def _get_service(
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CanonicalTranscriptService:
    return CanonicalTranscriptService(db=db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/meetings/{meeting_id}/transcript",
    response_model=CanonicalTranscript,
    summary="Get canonical transcript",
    tags=["Transcript"],
)
def get_canonical_transcript(
    meeting_id: UUID,
    version: Optional[int] = Query(
        None,
        ge=1,
        description="Specific version number to retrieve. Omit for latest.",
    ),
    service: CanonicalTranscriptService = Depends(_get_service),
) -> CanonicalTranscript:
    """
    Return the canonical transcript for a meeting.

    - Omit `version` to receive the current live view (built from DB rows).
    - Pass `?version=1` to retrieve the original AI-generated snapshot.
    - Pass `?version=N` for any human-edited version.
    """
    try:
        return service.get_canonical(meeting_id=meeting_id, version_number=version)
    except TranscriptNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/meetings/{meeting_id}/transcript/versions",
    response_model=TranscriptEditResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit human transcript edit",
    tags=["Transcript"],
)
def create_transcript_edit(
    meeting_id: UUID,
    request: TranscriptEditRequest,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> TranscriptEditResponse:
    """
    Submit corrected segment text.  A new versioned snapshot is created;
    the original AI output (version 1) is never overwritten.
    """
    service = CanonicalTranscriptService(db=db, tenant_id=tenant_ctx.tenant_id)
    try:
        new_version = service.create_edit_version(
            meeting_id=meeting_id,
            editor_user_id=tenant_ctx.user_id,
            request=request,
        )
    except TranscriptNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (SegmentValidationError, TranscriptVersioningError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    return TranscriptEditResponse(
        transcript_id=service.get_canonical(meeting_id=meeting_id).id,
        new_version_number=new_version,
        message=f"Edit version {new_version} created successfully.",
    )


@router.get(
    "/meetings/{meeting_id}/transcript/versions",
    response_model=List[TranscriptVersionMeta],
    summary="List transcript version history",
    tags=["Transcript"],
)
def list_transcript_versions(
    meeting_id: UUID,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> List[TranscriptVersionMeta]:
    """List all available transcript versions (provenance trail)."""
    transcript = (
        db.query(Transcript)
        .filter(
            Transcript.meeting_id == meeting_id,
            Transcript.tenant_id == tenant_ctx.tenant_id,
        )
        .first()
    )
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    versions = (
        db.query(TranscriptVersion)
        .filter(
            TranscriptVersion.transcript_id == transcript.id,
            TranscriptVersion.tenant_id == tenant_ctx.tenant_id,
        )
        .order_by(TranscriptVersion.version_number)
        .all()
    )

    return [
        TranscriptVersionMeta(
            version_number=v.version_number,
            source=v.source,
            edited_by_user_id=v.edited_by_user_id,
            edit_reason=v.edit_reason,
            created_at=v.created_at,
        )
        for v in versions
    ]
