from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.dependencies import get_current_user
from app.schemas.auth import CurrentUserContext
from app.intelligence.schemas import (
    MeetingIntelligenceResponse,
    TriggerIntelligenceRequest,
    IntelligenceRunSchema,
    TopicSchema,
    DecisionSchema,
    RiskSchema,
    QuestionSchema,
    CommitmentSchema,
)
from app.intelligence.extraction.service import MeetingIntelligenceService, IntelligenceNotFoundError

router = APIRouter(prefix="/meetings/{meeting_id}/intelligence", tags=["Meeting Intelligence"])


@router.post(
    "",
    response_model=MeetingIntelligenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger or get existing meeting intelligence analysis",
)
def analyze_meeting(
    meeting_id: UUID,
    request: Optional[TriggerIntelligenceRequest] = None,
    force_reprocess: bool = Query(False, description="Bypass idempotency cache"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    """
    Executes structural meeting intelligence extraction (Topics, Decisions, Risks, Questions, Commitments, Action Items)
    using the configured LLM provider and validates all evidence anchors against the canonical database.
    """
    service = MeetingIntelligenceService(db=db, tenant_id=current_user.organization_id)
    transcript_version = request.transcript_version if request else None

    try:
        return service.run_intelligence(
            meeting_id=meeting_id,
            transcript_version_number=transcript_version,
            force=force_reprocess,
        )
    except IntelligenceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intelligence extraction failed: {str(e)}",
        )


@router.get(
    "",
    response_model=MeetingIntelligenceResponse,
    summary="Get all latest intelligence artifacts for a meeting",
)
def get_intelligence(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = MeetingIntelligenceService(db=db, tenant_id=current_user.organization_id)
    try:
        return service.get_intelligence(meeting_id=meeting_id)
    except (IntelligenceNotFoundError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/runs",
    response_model=List[IntelligenceRunSchema],
    summary="List all intelligence extraction runs for this meeting",
)
def list_intelligence_runs(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = MeetingIntelligenceService(db=db, tenant_id=current_user.organization_id)
    runs = service.list_runs(meeting_id=meeting_id)
    return [IntelligenceRunSchema.model_validate(r) for r in runs]
