from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.security.dependencies import get_current_user
from app.schemas.auth import CurrentUserContext
from app.intelligence.schemas import (
    MeetingIntelligenceResponse,
    TriggerIntelligenceRequest,
    IntelligenceRunSchema,
)
from app.intelligence.extraction.service import MeetingIntelligenceService, IntelligenceNotFoundError
from app.models.meeting import Meeting
from app.models.media_asset import MediaAsset
from app.models.transcript import Transcript
from app.actions.models import ActionItem
from app.models.transcript_segment import TranscriptSegment
from app.intelligence.models import IntelligenceRun, Topic

router = APIRouter(prefix="/meetings/{meeting_id}/intelligence", tags=["Meeting Intelligence"])


def resolve_meeting(meeting_id_str: str, tenant_id: UUID, db: Session) -> Optional[Meeting]:
    """
    Resolve a meeting by UUID within the tenant.

    IMPORTANT: Never fall back to "any meeting with media" — that caused the
    One-Hit Wonder bug where subsequent meeting routes returned the first video's data.
    """
    try:
        uid = UUID(str(meeting_id_str).strip())
    except (ValueError, TypeError, AttributeError):
        return None

    return (
        db.query(Meeting)
        .filter(Meeting.id == uid, Meeting.tenant_id == tenant_id)
        .first()
    )


@router.post(
    "",
    response_model=MeetingIntelligenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger or get existing meeting intelligence analysis",
)
def analyze_meeting(
    meeting_id: str,
    request: Optional[TriggerIntelligenceRequest] = None,
    force_reprocess: bool = Query(False, description="Bypass idempotency cache"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    meeting = resolve_meeting(meeting_id, current_user.organization_id, db)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    service = MeetingIntelligenceService(db=db, tenant_id=current_user.organization_id)
    transcript_version = request.transcript_version if request else None

    try:
        return service.run_intelligence(
            meeting_id=meeting.id,
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
    status: str # "READY", "PROCESSING", "FAILED", "UNPROCESSED"
    summary: IntelligenceSummary
    actionItems: List[IntelligenceActionItem] = Field(default_factory=list)
    topics: List[IntelligenceTopic] = Field(default_factory=list)


@router.get(
    "",
    response_model=MeetingIntelligencePayload,
    summary="Get all latest intelligence artifacts for a meeting",
)
def get_intelligence(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> MeetingIntelligencePayload:
    meeting = resolve_meeting(meeting_id, current_user.organization_id, db)
    if not meeting:
        return MeetingIntelligencePayload(
            meetingId=str(meeting_id),
            status="UNPROCESSED",
            summary=IntelligenceSummary(executive=""),
            actionItems=[],
            topics=[],
        )

    actual_id = meeting.id
    service = MeetingIntelligenceService(db=db, tenant_id=meeting.tenant_id)

    # Check for in-flight or failed intelligence runs
    latest_run = (
        db.query(IntelligenceRun)
        .filter(IntelligenceRun.meeting_id == actual_id)
        .order_by(IntelligenceRun.created_at.desc())
        .first()
    )

    run = (
        db.query(IntelligenceRun)
        .filter(
            IntelligenceRun.meeting_id == actual_id,
            IntelligenceRun.status == "COMPLETED",
        )
        .order_by(IntelligenceRun.created_at.desc())
        .first()
    )

    # Lazy-trigger extraction only when a transcript exists and no completed run
    if not run:
        transcript = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == actual_id, Transcript.tenant_id == meeting.tenant_id)
            .first()
        )
        if transcript:
            try:
                service.run_intelligence(meeting_id=actual_id)
                run = (
                    db.query(IntelligenceRun)
                    .filter(
                        IntelligenceRun.meeting_id == actual_id,
                        IntelligenceRun.status == "COMPLETED",
                    )
                    .order_by(IntelligenceRun.created_at.desc())
                    .first()
                )
            except Exception:
                # Surface processing/failed state honestly — never invent topics
                if latest_run and latest_run.status in ("PENDING", "PROCESSING", "IN_PROGRESS"):
                    return MeetingIntelligencePayload(
                        meetingId=str(actual_id),
                        status="PROCESSING",
                        summary=IntelligenceSummary(executive=""),
                        actionItems=[],
                        topics=[],
                    )
                return MeetingIntelligencePayload(
                    meetingId=str(actual_id),
                    status="FAILED",
                    summary=IntelligenceSummary(executive=""),
                    actionItems=[],
                    topics=[],
                )
        else:
            # Media may still be in the ASR pipeline
            media = (
                db.query(MediaAsset)
                .filter(MediaAsset.meeting_id == actual_id, MediaAsset.tenant_id == meeting.tenant_id)
                .first()
            )
            status_out = "PROCESSING" if media else "UNPROCESSED"
            return MeetingIntelligencePayload(
                meetingId=str(actual_id),
                status=status_out,
                summary=IntelligenceSummary(executive=""),
                actionItems=[],
                topics=[],
            )

    topics = (
        db.query(Topic)
        .filter(Topic.meeting_id == actual_id)
        .order_by(Topic.importance_score.desc())
        .all()
    )

    actions = (
        db.query(ActionItem)
        .options(selectinload(ActionItem.evidence_items))
        .filter(ActionItem.meeting_id == actual_id)
        .order_by(ActionItem.created_at.asc())
        .all()
    )

    topics_payload = [
        IntelligenceTopic(
            id=str(t.id),
            title=t.title,
            description=t.summary or "",
            evidence=[EvidenceAnchor(timestampStart=float(t.start_seconds or 0))],
        )
        for t in topics
    ]

    action_items_payload = []
    for a in actions:
        start_time = 0.0
        if a.evidence_items:
            try:
                first_evidence_seg_id = a.evidence_items[0].segment_id
                seg = db.query(TranscriptSegment).filter(TranscriptSegment.id == first_evidence_seg_id).first()
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

    if topics:
        executive_summary = " ".join([t.summary for t in topics[:3] if t.summary])
    elif run and getattr(run, "executive_summary", None):
        executive_summary = run.executive_summary
    else:
        executive_summary = ""

    return MeetingIntelligencePayload(
        meetingId=str(actual_id),
        status="READY",
        summary=IntelligenceSummary(executive=executive_summary or "Meeting summary is available."),
        actionItems=action_items_payload,
        topics=topics_payload,
    )


@router.get(
    "/runs",
    response_model=List[IntelligenceRunSchema],
    summary="List all intelligence extraction runs for this meeting",
)
def list_intelligence_runs(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    meeting = resolve_meeting(meeting_id, current_user.organization_id, db)
    if not meeting:
        return []
    service = MeetingIntelligenceService(db=db, tenant_id=meeting.tenant_id)
    runs = service.list_runs(meeting_id=meeting.id)
    return [IntelligenceRunSchema.model_validate(r) for r in runs]
