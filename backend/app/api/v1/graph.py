"""
Phase 24 – Knowledge Graph API Endpoints

Provides authenticated endpoints for querying knowledge entities,
traversing organizational relationship subgraphs, and running graph extraction.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.service import AuthorizationService
from app.core.database import get_db
from app.graph.extraction.service import GraphExtractionService
from app.graph.models import KnowledgeEntity
from app.graph.retrieval.traversal import GraphTraversalEngine
from app.graph.schemas import (
    EntitySchema,
    EntitySearchResponse,
    GraphExtractionResponse,
    SubGraphResponse,
)
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter()


@router.get(
    "/entities",
    response_model=EntitySearchResponse,
    summary="Search or list knowledge graph entities",
)
def list_entities(
    query: Optional[str] = Query(None, description="Search term for entity names or aliases"),
    entity_type: Optional[str] = Query(None, description="Optional filter by entity type"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> EntitySearchResponse:
    tenant_id = current_user.organization_id
    q = db.query(KnowledgeEntity).filter(KnowledgeEntity.tenant_id == tenant_id)

    if entity_type:
        q = q.filter(KnowledgeEntity.entity_type == entity_type.upper())

    if query:
        traversal = GraphTraversalEngine(db=db, tenant_id=tenant_id)
        entities = traversal.find_entities_by_name(query, limit=limit)
        return EntitySearchResponse(
            total=len(entities),
            entities=[EntitySchema.model_validate(e) for e in entities],
        )

    entities = q.order_by(KnowledgeEntity.name.asc()).limit(limit).all()
    total = q.count()
    return EntitySearchResponse(
        total=total,
        entities=[EntitySchema.model_validate(e) for e in entities],
    )


@router.get(
    "/entities/{entity_id}/subgraph",
    response_model=SubGraphResponse,
    summary="Retrieve multi-hop subgraph neighborhood for an entity",
)
def get_entity_subgraph(
    entity_id: UUID,
    depth: int = Query(1, ge=1, le=3, description="Hop depth for relationship traversal"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> SubGraphResponse:
    auth_service = AuthorizationService(db=db)
    scope = auth_service.resolve_scope(current_user=current_user)

    engine = GraphTraversalEngine(db=db, tenant_id=current_user.organization_id)
    subgraph = engine.traverse_subgraph(
        root_entity_id=entity_id,
        depth=depth,
        scope=scope,
    )
    if not subgraph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found or cross-tenant access denied.",
        )
    return subgraph


@router.post(
    "/extract/{meeting_id}",
    response_model=GraphExtractionResponse,
    summary="Trigger knowledge graph extraction for a meeting",
)
def extract_graph_from_meeting(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> GraphExtractionResponse:
    auth_service = AuthorizationService(db=db)
    scope = auth_service.resolve_scope(current_user=current_user, requested_meeting_id=meeting_id)

    service = GraphExtractionService(db=db, tenant_id=current_user.organization_id)
    return service.extract_from_meeting(meeting_id=meeting_id)
