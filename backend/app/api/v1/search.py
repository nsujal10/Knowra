"""
Phase 20 – Search REST Endpoints

Implements POST /api/v1/search accepting structured filters and returning
deduplicated hybrid results with exact canonical transcript citations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.knowledge.retrieval.retriever import HybridRetriever
from app.knowledge.schemas import HybridSearchResponse, SearchResultItem
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Enterprise Search"])


class SearchRequest(BaseModel):
    query: str = Field(..., description="Semantic or keyword query text")
    meeting_id: Optional[UUID] = Field(None, description="Optional meeting scope filter")
    limit: int = Field(10, ge=1, le=50, description="Max results to return")
    vector_weight: float = Field(0.5, ge=0.0, le=1.0, description="RRF weight for vector search")
    keyword_weight: float = Field(0.5, ge=0.0, le=1.0, description="RRF weight for keyword search")


@router.post(
    "/search",
    response_model=HybridSearchResponse,
    summary="Execute hybrid search (pgvector + FTS + RRF + reranking) with canonical citations",
)
def execute_search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    retriever = HybridRetriever(db=db, tenant_id=current_user.organization_id)
    return retriever.search(
        query=payload.query,
        limit=payload.limit,
        meeting_id=payload.meeting_id,
        vector_weight=payload.vector_weight,
        keyword_weight=payload.keyword_weight,
    )
