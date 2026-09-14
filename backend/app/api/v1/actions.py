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
)
from app.actions.service import ActionItemService, InvalidStatusTransitionError

router = APIRouter(tags=["Action Items"])


@router.post(
    "/meetings/{meeting_id}/actions",
    response_model=ActionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an action item manually for a meeting",
)
def create_action_item(
    meeting_id: UUID,
    payload: ActionItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    item = service.ingest_extracted_action_item(
        meeting_id=meeting_id,
        title=payload.title,
        description=payload.description,
        owner_raw=payload.owner_raw,
        due_date_raw=payload.due_date_raw,
        priority=payload.priority,
        evidence_segment_ids=payload.evidence_segment_ids,
    )
    if payload.owner_id:
        confirm_data = ActionItemConfirmRequest(owner_id=payload.owner_id, due_date=payload.due_date)
        item = service.confirm_action_item(item.id, actor_user_id=current_user.user_id, confirm_data=confirm_data)
    return item


@router.get(
    "/meetings/{meeting_id}/actions",
    response_model=ActionItemListResponse,
    summary="List action items for a meeting",
)
def list_meeting_actions(
    meeting_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = ActionItemService(db=db, tenant_id=current_user.organization_id)
    items = service.list_meeting_action_items(
        meeting_id=meeting_id,
        status=status_filter,
        owner_id=owner_id,
    )
    return ActionItemListResponse(
        items=[ActionItemResponse.model_validate(item) for item in items],
        total=len(items),
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
