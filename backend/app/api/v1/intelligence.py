from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

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


from pydantic import BaseModel, Field
from app.models.processing_job import ProcessingJob
from app.models.media_asset import MediaAsset
from app.models.transcript import Transcript
from app.actions.models import ActionItem
from app.models.transcript_segment import TranscriptSegment
from app.intelligence.models import IntelligenceRun, Topic

class EvidenceAnchor(BaseModel):
    timestampStart: float = 0.0

class IntelligenceActionItem(BaseModel):
    id: str
    owner: str
    task: str
    evidence: List[EvidenceAnchor] = Field(default_factory=list)

class IntelligenceTopic(BaseModel):
    id: str
    title: str
    description: str
    evidence: List[EvidenceAnchor] = Field(default_factory=list)

class IntelligenceSummary(BaseModel):
    executive: str

class MeetingIntelligencePayload(BaseModel):
    meetingId: str
    status: str # "READY", "PROCESSING", "FAILED"
    summary: IntelligenceSummary
    actionItems: List[IntelligenceActionItem] = Field(default_factory=list)
    topics: List[IntelligenceTopic] = Field(default_factory=list)

@router.get(
    "",
    response_model=MeetingIntelligencePayload,
    summary="Get all latest intelligence artifacts for a meeting",
)
def get_intelligence(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> MeetingIntelligencePayload:
    service = MeetingIntelligenceService(db=db, tenant_id=current_user.organization_id)
    
    # 1. Look up existing completed intelligence run
    run = (
        db.query(IntelligenceRun)
        .filter(
            IntelligenceRun.meeting_id == meeting_id,
            IntelligenceRun.tenant_id == current_user.organization_id,
            IntelligenceRun.status == "COMPLETED",
        )
        .order_by(IntelligenceRun.created_at.desc())
        .first()
    )

    # 2. If no completed run exists, check if processing or attempt automatic extraction
    if not run:
        media = db.query(MediaAsset).filter(
            MediaAsset.meeting_id == meeting_id,
            MediaAsset.tenant_id == current_user.organization_id,
        ).first()

        job = None
        if media:
            job = (
                db.query(ProcessingJob)
                .filter(
                    ProcessingJob.media_asset_id == media.id,
                    ProcessingJob.tenant_id == current_user.organization_id,
                    ProcessingJob.task_name.in_(["TRANSCRIPTION", "INTELLIGENCE", "DIARIZATION"]),
                )
                .order_by(ProcessingJob.created_at.desc())
                .first()
            )

        # Check if canonical transcript exists so we can run intelligence
        transcript_exists = (
            db.query(Transcript)
            .filter(
                Transcript.meeting_id == meeting_id,
                Transcript.tenant_id == current_user.organization_id,
            )
            .first()
        )

        if not transcript_exists and job and job.status in ["PENDING", "PROCESSING", "IN_PROGRESS"]:
            return MeetingIntelligencePayload(
                meetingId=str(meeting_id),
                status="PROCESSING",
                summary=IntelligenceSummary(executive=""),
                actionItems=[],
                topics=[],
            )

        # Attempt to run intelligence extraction if transcript is ready
        try:
            service.run_intelligence(meeting_id=meeting_id)
            run = (
                db.query(IntelligenceRun)
                .filter(
                    IntelligenceRun.meeting_id == meeting_id,
                    IntelligenceRun.tenant_id == current_user.organization_id,
                    IntelligenceRun.status == "COMPLETED",
                )
                .order_by(IntelligenceRun.created_at.desc())
                .first()
            )
        except Exception:
            return MeetingIntelligencePayload(
                meetingId=str(meeting_id),
                status="PROCESSING",
                summary=IntelligenceSummary(executive=""),
                actionItems=[],
                topics=[],
            )

    if not run:
        return MeetingIntelligencePayload(
            meetingId=str(meeting_id),
            status="PROCESSING",
            summary=IntelligenceSummary(executive=""),
            actionItems=[],
            topics=[],
        )

    # 3. Fetch extracted topics
    topics = (
        db.query(Topic)
        .filter(Topic.intelligence_run_id == run.id, Topic.tenant_id == current_user.organization_id)
        .order_by(Topic.importance_score.desc())
        .all()
    )
    topics_payload = [
        IntelligenceTopic(
            id=str(t.id),
            title=t.title,
            description=t.summary,
            evidence=[EvidenceAnchor(timestampStart=float(t.start_seconds or 0))],
        )
        for t in topics
    ]

    # 4. Fetch extracted action items
    actions = (
        db.query(ActionItem)
        .options(selectinload(ActionItem.evidence_items))
        .filter(ActionItem.meeting_id == meeting_id, ActionItem.tenant_id == current_user.organization_id)
        .order_by(ActionItem.created_at.asc())
        .all()
    )
    action_items_payload = []
    for a in actions:
        start_time = 0.0
        if a.evidence_items:
            try:
                first_seg_id = a.evidence_items[0].segment_id
                seg = db.query(TranscriptSegment).filter(TranscriptSegment.id == first_seg_id).first()
                if seg and seg.start_seconds is not None:
                    start_time = float(seg.start_seconds)
            except Exception:
                pass
        action_items_payload.append(
            IntelligenceActionItem(
                id=str(a.id),
                owner=a.owner_raw or "Team",
                task=a.description or a.title,
                evidence=[EvidenceAnchor(timestampStart=start_time)],
            )
        )

    # 5. Build executive summary
    if topics:
        executive_summary = " ".join([t.summary for t in topics[:3]])
    else:
        executive_summary = "Meeting summary is available."

    return MeetingIntelligencePayload(
        meetingId=str(meeting_id),
        status="READY",
        summary=IntelligenceSummary(executive=executive_summary),
        actionItems=action_items_payload,
        topics=topics_payload,
    )


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
