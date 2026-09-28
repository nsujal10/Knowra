"""
Phase 17 – Decision Intelligence REST Endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.decisions.models import Decision
from app.decisions.resolver import DecisionResolutionService
from app.decisions.schemas import (
    DecisionCreateRequest,
    DecisionGraphResponse,
    DecisionListResponse,
    DecisionRelationshipCreate,
    DecisionRelationshipSchema,
    DecisionResponse,
    EnterpriseDecisionsResponse,
    DecisionItemDetail,
    DecisionsMetrics,
    MeetingSummaryItem,
)
from app.decisions.sync import sync_meeting_decisions_to_enterprise, infer_decision_category
from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user
from sqlalchemy import func, or_

router = APIRouter(tags=["Decision Intelligence"])


def build_decisions_response(
    db: Session,
    tenant_id: UUID,
    meeting_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> EnterpriseDecisionsResponse:
    # 1. Sync any unmaterialized meeting decisions
    try:
        sync_meeting_decisions_to_enterprise(db, tenant_id=tenant_id)
    except Exception:
        pass

    # 2. Query all decisions for metrics & meetings filter
    all_decisions_query = db.query(Decision).filter(Decision.tenant_id == tenant_id)
    if meeting_id:
        all_decisions_query = all_decisions_query.filter(Decision.meeting_id == meeting_id)

    all_decisions = all_decisions_query.all()
    total_count = len(all_decisions)
    confirmed_count = sum(1 for d in all_decisions if d.status in ("CONFIRMED", "APPROVED"))
    superseded_count = sum(1 for d in all_decisions if d.status == "SUPERSEDED")

    pct = int((confirmed_count / total_count) * 100) if total_count > 0 else 100
    consensus_level = f"{pct}% Unanimous" if pct == 100 else f"{pct}% Consensus"

    # Gather unique meetings
    meetings_map = {}
    for d in (
        db.query(Decision.meeting_id, Meeting.title)
        .join(Meeting, Decision.meeting_id == Meeting.id)
        .filter(Decision.tenant_id == tenant_id)
        .all()
    ):
        mid_str = str(d[0])
        if mid_str not in meetings_map:
            meetings_map[mid_str] = {"id": mid_str, "title": d[1], "count": 0}
        meetings_map[mid_str]["count"] += 1

    meeting_summary_items = [
        MeetingSummaryItem(id=v["id"], title=v["title"], decision_count=v["count"])
        for v in meetings_map.values()
    ]

    # 3. Filtered items query
    query = (
        db.query(Decision, Meeting.title.label("meeting_title"))
        .join(Meeting, Decision.meeting_id == Meeting.id)
        .filter(Decision.tenant_id == tenant_id)
    )

    if meeting_id:
        query = query.filter(Decision.meeting_id == meeting_id)

    if status_filter and status_filter.upper() != "ALL":
        clean_status = status_filter.upper()
        if clean_status == "APPROVED":
            query = query.filter(Decision.status.in_(["CONFIRMED", "APPROVED"]))
        else:
            query = query.filter(Decision.status == clean_status)

    if search:
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Decision.title).like(term),
                func.lower(Decision.description).like(term),
                func.lower(Decision.decided_by_raw).like(term),
            )
        )

    raw_items = query.order_by(Decision.created_at.desc()).all()

    # Format details with segments / timestamps
    details: List[DecisionItemDetail] = []
    for dec, m_title in raw_items:
        # Topic / Category
        cat = (
            dec.topics[0].topic_name.upper()
            if dec.topics
            else infer_decision_category(f"{dec.title} {dec.description}")
        )
        if category and category.upper() != "ALL" and cat != category.upper():
            continue

        snippet = None
        start_seconds = None
        ts_str = "0:00"
        if dec.evidence_segment_ids:
            try:
                first_seg_id = UUID(str(dec.evidence_segment_ids[0]))
                seg = db.query(TranscriptSegment).filter(TranscriptSegment.id == first_seg_id).first()
                if seg:
                    snippet = seg.text
                    start_seconds = seg.start_seconds
                    if start_seconds is not None:
                        ts_str = f"{int(start_seconds // 60)}:{int(start_seconds % 60):02d}"
            except Exception:
                pass

        status_disp = "APPROVED" if dec.status == "CONFIRMED" else dec.status

        details.append(
            DecisionItemDetail(
                id=dec.id,
                meeting_id=dec.meeting_id,
                meeting_title=m_title,
                title=dec.title,
                description=dec.description,
                rationale=dec.rationale,
                status=status_disp,
                impact_level=dec.impact_level,
                category=cat,
                decided_by=dec.decided_by_raw or "Executive Committee",
                decided_by_raw=dec.decided_by_raw,
                timestamp=ts_str,
                start_seconds=start_seconds,
                evidence_snippet=snippet,
                evidence_segment_ids=[UUID(str(x)) for x in (dec.evidence_segment_ids or []) if isinstance(x, (str, UUID))],
                tenant_id=dec.tenant_id,
                created_at=dec.created_at,
            )
        )

    return EnterpriseDecisionsResponse(
        items=details,
        total=len(details),
        metrics=DecisionsMetrics(
            total_decisions=total_count,
            consensus_level=consensus_level,
            ai_verified="Strict RBAC • Confidential Guard",
            confirmed_count=confirmed_count,
            superseded_count=superseded_count,
        ),
        meetings=meeting_summary_items,
    )


@router.get(
    "/decisions",
    response_model=EnterpriseDecisionsResponse,
    summary="List enterprise decisions across meetings with filters and governance metrics",
)
def list_global_decisions(
    meeting_id: Optional[UUID] = Query(None, description="Optional meeting filter"),
    status: Optional[str] = Query(None, description="Filter by status (APPROVED, SUPERSEDED, etc.)"),
    category: Optional[str] = Query(None, description="Filter by category (ARCHITECTURE, ENGINEERING, etc.)"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    return build_decisions_response(
        db=db,
        tenant_id=current_user.organization_id,
        meeting_id=meeting_id,
        status_filter=status,
        category=category,
        search=search,
    )


@router.post(
    "/meetings/{meeting_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a decision with evidence segments",
)
def create_decision(
    meeting_id: UUID,
    payload: DecisionCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = DecisionResolutionService(db=db, tenant_id=current_user.organization_id)
    decision = service.create_decision(
        meeting_id=meeting_id,
        payload=payload,
        actor_user_id=current_user.user_id,
    )
    return decision


@router.get(
    "/meetings/{meeting_id}/decisions",
    response_model=EnterpriseDecisionsResponse,
    summary="List decisions made in a meeting",
)
def list_meeting_decisions(
    meeting_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    return build_decisions_response(
        db=db,
        tenant_id=current_user.organization_id,
        meeting_id=meeting_id,
        status_filter=status_filter,
        category=category,
        search=search,
    )



@router.get(
    "/decisions/latest-for-topic",
    response_model=Optional[DecisionResponse],
    summary="Retrieve the current active decision governing a specific topic/entity",
)
def get_latest_decision_for_topic(
    topic: str = Query(..., description="Topic name or query string"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = DecisionResolutionService(db=db, tenant_id=current_user.organization_id)
    latest = service.get_latest_decision_for_topic(topic)
    return latest


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
    summary="Get single decision details by ID",
)
def get_decision(
    decision_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    decision = (
        db.query(Decision)
        .filter(
            Decision.id == decision_id,
            Decision.tenant_id == current_user.organization_id,
        )
        .first()
    )
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found or tenant unauthorized",
        )
    return decision


@router.get(
    "/decisions/{decision_id}/graph",
    response_model=DecisionGraphResponse,
    summary="Get decision graph lineage (ancestors, descendants, superseding edges)",
)
def get_decision_graph(
    decision_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = DecisionResolutionService(db=db, tenant_id=current_user.organization_id)
    return service.get_decision_graph(decision_id)


@router.post(
    "/decisions/{decision_id}/relationships",
    response_model=DecisionRelationshipSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a directed relationship between decisions (e.g. SUPERSEDES, REVERSES)",
)
def add_decision_relationship(
    decision_id: UUID,
    payload: DecisionRelationshipCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = DecisionResolutionService(db=db, tenant_id=current_user.organization_id)
    try:
        rel = service.add_manual_relationship(
            source_decision_id=decision_id,
            payload=payload,
            actor_user_id=current_user.user_id,
        )
        return rel
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
