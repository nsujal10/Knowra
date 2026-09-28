from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.dependencies import get_current_user
from app.schemas.auth import CurrentUserContext
from app.actions.models import ActionItem
from app.actions.schemas import (
    ActionItemCreate,
    ActionItemUpdate,
    ActionItemConfirmRequest,
    ActionItemStatusTransitionRequest,
    ActionItemResponse,
    ActionItemListResponse,
    ActionItemCommentCreate,
    ActionItemCommentSchema,
    ActionItemDetail,
    ActionsMetrics,
    ActionMeetingSummary,
    EnterpriseActionsResponse,
)
from app.actions.service import ActionItemService, InvalidStatusTransitionError
from app.actions.sync import sync_commitments_to_action_items
from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment
from sqlalchemy import func, or_

router = APIRouter(tags=["Action Items"])


def build_actions_response(
    db: Session,
    tenant_id: UUID,
    meeting_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    priority: Optional[str] = None,
    owner: Optional[str] = None,
    search: Optional[str] = None,
) -> EnterpriseActionsResponse:
    try:
        sync_commitments_to_action_items(db, tenant_id=tenant_id)
    except Exception:
        pass

    all_query = db.query(ActionItem).filter(ActionItem.tenant_id == tenant_id)
    if meeting_id:
        all_query = all_query.filter(ActionItem.meeting_id == meeting_id)

    all_items = all_query.all()
    total_items = len(all_items)
    completed_count = sum(1 for a in all_items if a.status == "COMPLETED")
    pending_count = total_items - completed_count
    urgent_count = sum(1 for a in all_items if a.priority in ("URGENT", "HIGH") and a.status != "COMPLETED")
    pct = int((completed_count / total_items) * 100) if total_items > 0 else 0
    completion_rate = f"{pct}% Done"

    meetings_map = {}
    for item in (
        db.query(ActionItem.meeting_id, Meeting.title)
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(ActionItem.tenant_id == tenant_id)
        .all()
    ):
        mid_str = str(item[0])
        if mid_str not in meetings_map:
            meetings_map[mid_str] = {"id": mid_str, "title": item[1], "count": 0}
        meetings_map[mid_str]["count"] += 1

    meeting_summaries = [
        ActionMeetingSummary(id=v["id"], title=v["title"], action_count=v["count"])
        for v in meetings_map.values()
    ]

    owners = sorted(list({a.owner_raw.strip() for a in all_items if a.owner_raw and a.owner_raw.strip()}))

    query = (
        db.query(ActionItem, Meeting.title.label("meeting_title"))
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(ActionItem.tenant_id == tenant_id)
    )

    if meeting_id:
        query = query.filter(ActionItem.meeting_id == meeting_id)

    if status_filter and status_filter.upper() != "ALL":
        clean = status_filter.upper()
        if clean in ("PENDING", "OPEN"):
            query = query.filter(ActionItem.status != "COMPLETED")
        elif clean == "COMPLETED":
            query = query.filter(ActionItem.status == "COMPLETED")
        else:
            query = query.filter(ActionItem.status == clean)

    if priority and priority.upper() != "ALL":
        query = query.filter(ActionItem.priority == priority.upper())

    if owner and owner.upper() != "ALL":
        query = query.filter(ActionItem.owner_raw == owner)

    if search:
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(ActionItem.title).like(term),
                func.lower(ActionItem.description).like(term),
                func.lower(ActionItem.owner_raw).like(term),
                func.lower(Meeting.title).like(term),
            )
        )

    raw_items = query.order_by(ActionItem.created_at.desc()).all()

    details: List[ActionItemDetail] = []
    for it, m_title in raw_items:
        snippet = None
        start_seconds = None
        ts_str = "0:00"
        if it.evidence_items:
            try:
                first_ev = it.evidence_items[0]
                snippet = first_ev.snippet
                seg = db.query(TranscriptSegment).filter(TranscriptSegment.id == first_ev.segment_id).first()
                if seg:
                    if not snippet:
                        snippet = seg.text
                    start_seconds = seg.start_seconds
                    if start_seconds is not None:
                        ts_str = f"{int(start_seconds // 60)}:{int(start_seconds % 60):02d}"
            except Exception:
                pass

        details.append(
            ActionItemDetail(
                id=it.id,
                meeting_id=it.meeting_id,
                meeting_title=m_title,
                title=it.title,
                description=it.description,
                status=it.status,
                priority=it.priority or "MEDIUM",
                due_date=it.due_date,
                due_date_raw=it.due_date_raw,
                owner_raw=it.owner_raw,
                assignee=it.owner_raw or "Team",
                owner_id=it.owner_id,
                timestamp=ts_str,
                start_seconds=start_seconds,
                evidence_snippet=snippet,
                evidence_segment_ids=[e.segment_id for e in it.evidence_items],
                created_at=it.created_at,
                completed_at=it.completed_at,
            )
        )

    return EnterpriseActionsResponse(
        items=details,
        total=len(details),
        metrics=ActionsMetrics(
            total_items=total_items,
            pending_count=pending_count,
            completed_count=completed_count,
            urgent_count=urgent_count,
            completion_rate=completion_rate,
        ),
        meetings=meeting_summaries,
        owners=owners,
    )


@router.get(
    "/actions",
    response_model=EnterpriseActionsResponse,
    summary="List enterprise action items across meetings with filters and governance metrics",
)
def list_global_actions(
    meeting_id: Optional[UUID] = Query(None, description="Optional meeting filter"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, COMPLETED, OPEN, etc.)"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, MEDIUM, HIGH, URGENT)"),
    owner: Optional[str] = Query(None, description="Filter by owner name"),
    search: Optional[str] = Query(None, description="Search keyword in title, description, or owner"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    return build_actions_response(
        db=db,
        tenant_id=current_user.organization_id,
        meeting_id=meeting_id,
        status_filter=status,
        priority=priority,
        owner=owner,
        search=search,
    )


@router.patch(
    "/actions/{action_id}/toggle",
    response_model=ActionItemDetail,
    summary="Toggle action item status between COMPLETED and OPEN",
)
def toggle_action_item_status(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    item = service.get_action_item(action_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")

    try:
        if item.status == "COMPLETED":
            updated = service.transition_status(
                action_item_id=action_id,
                new_status="OPEN",
                actor_user_id=current_user.user_id,
                reason="User reopened task via checklist",
            )
        elif item.status == "REVIEW_REQUIRED":
            service.transition_status(
                action_item_id=action_id,
                new_status="OPEN",
                actor_user_id=current_user.user_id,
                reason="Auto-confirmed on checklist toggle",
            )
            updated = service.transition_status(
                action_item_id=action_id,
                new_status="COMPLETED",
                actor_user_id=current_user.user_id,
                reason="User toggled status via checklist interface",
            )
        else:
            updated = service.transition_status(
                action_item_id=action_id,
                new_status="COMPLETED",
                actor_user_id=current_user.user_id,
                reason="User toggled status via checklist interface",
            )
        return ActionItemDetail(
            id=updated.id,
            meeting_id=updated.meeting_id,
            title=updated.title,
            description=updated.description,
            status=updated.status,
            priority=updated.priority or "MEDIUM",
            due_date=updated.due_date,
            due_date_raw=updated.due_date_raw,
            owner_raw=updated.owner_raw,
            assignee=updated.owner_raw or "Team",
            owner_id=updated.owner_id,
            created_at=updated.created_at,
            completed_at=updated.completed_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/meetings/{meeting_id}/actions",
    response_model=EnterpriseActionsResponse,
    summary="List action items for a meeting with metrics",
)
def list_meeting_actions(
    meeting_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    return build_actions_response(
        db=db,
        tenant_id=current_user.organization_id,
        meeting_id=meeting_id,
        status_filter=status_filter,
        priority=priority,
        owner=owner,
        search=search,
    )


@router.get(
    "/actions/{action_id}",
    response_model=ActionItemResponse,
    summary="Get action item by ID with evidence, events, and comments",
)
def get_action_item(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    item = service.get_action_item(action_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")
    return ActionItemResponse.model_validate(item)


@router.post(
    "/actions/{action_id}/confirm",
    response_model=ActionItemResponse,
    summary="Confirm candidate action item (transitions REVIEW_REQUIRED to OPEN)",
)
def confirm_action_item(
    action_id: UUID,
    payload: Optional[ActionItemConfirmRequest] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    try:
        item = service.confirm_action_item(
            action_item_id=action_id,
            actor_user_id=current_user.user_id,
            confirm_data=payload,
        )
        return ActionItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/actions/{action_id}/transition",
    response_model=ActionItemResponse,
    summary="Transition action item lifecycle status (OPEN -> IN_PROGRESS -> COMPLETED)",
)
def transition_status(
    action_id: UUID,
    payload: ActionItemStatusTransitionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    try:
        item = service.transition_status(
            action_item_id=action_id,
            new_status=payload.status,
            actor_user_id=current_user.user_id,
            reason=payload.reason,
        )
        return ActionItemResponse.model_validate(item)
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/actions/{action_id}",
    response_model=ActionItemResponse,
    summary="Update action item details",
)
def update_action_item(
    action_id: UUID,
    payload: ActionItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    try:
        item = service.update_action_item(
            action_item_id=action_id,
            update_data=payload,
            actor_user_id=current_user.user_id,
        )
        return ActionItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/actions/{action_id}/comments",
    response_model=ActionItemCommentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to an action item",
)
def add_comment(
    action_id: UUID,
    payload: ActionItemCommentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    try:
        comment = service.add_comment(
            action_item_id=action_id,
            user_id=current_user.user_id,
            comment_text=payload.comment_text,
        )
        return ActionItemCommentSchema.model_validate(comment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
