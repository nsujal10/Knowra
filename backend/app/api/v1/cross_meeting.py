"""
Phase 23 – Cross-Meeting Intelligence API Endpoints

Provides authenticated endpoints for multi-meeting query decomposition,
chronological timeline building, and decision evolution tracking.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.service import AuthorizationService
from app.core.database import get_db
from app.intelligence.cross_meeting.decomposer import QueryDecomposer
from app.intelligence.cross_meeting.schemas import (
    CrossMeetingQueryRequest,
    DecisionEvolutionResponse,
    DecomposedQueryPlan,
    TimelineResponse,
)
from app.intelligence.cross_meeting.timeline import TimelineBuilder
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter()


@router.get(
    "/topics/{topic_name}/timeline",
    response_model=TimelineResponse,
    summary="Retrieve cross-meeting chronological timeline for a topic",
)
def get_topic_timeline(
    topic_name: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> TimelineResponse:
    auth_service = AuthorizationService(db=db)
    scope = auth_service.resolve_scope(current_user=current_user)

    builder = TimelineBuilder(db=db)
    return builder.build_timeline(
        scope=scope,
        entity_or_topic=topic_name,
        limit=limit,
    )


@router.get(
    "/decisions/{decision_id}/evolution",
    response_model=DecisionEvolutionResponse,
    summary="Retrieve decision evolution and supersession lineage across meetings",
)
def get_decision_evolution(
    decision_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> DecisionEvolutionResponse:
    auth_service = AuthorizationService(db=db)
    scope = auth_service.resolve_scope(current_user=current_user)

    builder = TimelineBuilder(db=db)
    evolution = builder.build_decision_evolution(scope=scope, decision_id=decision_id)
    if evolution.total_versions == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found or access denied.",
        )
    return evolution


@router.post(
    "/timeline",
    response_model=TimelineResponse,
    summary="Generate custom multi-meeting chronological timeline",
)
def generate_cross_meeting_timeline(
    request: CrossMeetingQueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> TimelineResponse:
    auth_service = AuthorizationService(db=db)
    scope = auth_service.resolve_scope(current_user=current_user)

    target = request.entity_or_topic or request.query
    builder = TimelineBuilder(db=db)
    return builder.build_timeline(
        scope=scope,
        entity_or_topic=target,
        meeting_ids=request.meeting_ids,
        limit=request.limit_events,
    )


from pydantic import BaseModel

class DecomposeQueryRequest(BaseModel):
    query: str

@router.post(
    "/decompose",
    response_model=DecomposedQueryPlan,
    summary="Decompose complex question into cross-meeting sub-tasks",
)
def decompose_query(
    request: Optional[DecomposeQueryRequest] = None,
    query: Optional[str] = Query(None),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> DecomposedQueryPlan:
    target_query = (request.query if request else None) or query
    if not target_query or len(target_query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query parameter or body field required (min length 2).",
        )
    decomposer = QueryDecomposer()
    return decomposer.decompose(query=target_query)
