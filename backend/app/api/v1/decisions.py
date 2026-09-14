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
)
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Decision Intelligence"])


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
    response_model=DecisionListResponse,
    summary="List decisions made in a meeting",
)
def list_meeting_decisions(
    meeting_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    query = (
        db.query(Decision)
        .filter(
            Decision.meeting_id == meeting_id,
            Decision.tenant_id == current_user.organization_id,
        )
    )
    if status_filter:
        query = query.filter(Decision.status == status_filter.upper())

    items = query.order_by(Decision.created_at.desc()).all()
    return DecisionListResponse(items=items, total=len(items))


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
