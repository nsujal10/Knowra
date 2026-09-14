"""
Phase 18 – Knowledge Chunking & Hybrid Retrieval REST Endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.knowledge.chunking import SemanticChunker
from app.knowledge.embeddings.gateway import EmbeddingGateway
from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment
from app.knowledge.retrieval import HybridRetrievalService
from app.knowledge.schemas import HybridSearchResponse, KnowledgeChunkResponse
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Knowledge & Search"])


@router.post(
    "/meetings/{meeting_id}/chunk-and-index",
    response_model=List[KnowledgeChunkResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Trigger semantic chunking, embedding generation, and indexing for a meeting transcript",
)
def chunk_and_index_meeting(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    # Verify meeting belongs to tenant
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.tenant_id == current_user.organization_id)
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or tenant unauthorized",
        )

    # Locate canonical transcript
    transcript = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id, Transcript.tenant_id == current_user.organization_id)
        .first()
    )
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found for this meeting",
        )

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.transcript_id == transcript.id)
        .order_by(TranscriptSegment.sequence_number.asc())
        .all()
    )
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript contains no segments to chunk",
        )

    # Clean existing chunks for this meeting to prevent duplicates
    existing_chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.meeting_id == meeting_id, KnowledgeChunk.tenant_id == current_user.organization_id)
        .all()
    )
    for ec in existing_chunks:
        db.delete(ec)
    db.flush()

    # Semantic Chunking
    chunker = SemanticChunker()
    raw_chunks = chunker.chunk_segments(segments)

    # Embeddings
    gateway = EmbeddingGateway()
    provider = gateway.get_provider()

    created_chunks: List[KnowledgeChunk] = []
    for idx, rc in enumerate(raw_chunks):
        emb = provider.embed_text(rc.content)
        k_chunk = KnowledgeChunk(
            tenant_id=current_user.organization_id,
            meeting_id=meeting_id,
            transcript_id=transcript.id,
            content=rc.content,
            chunk_index=idx,
            token_count=rc.token_count,
            primary_topic=rc.primary_topic,
            speaker_names=rc.speaker_names,
            start_seconds=rc.start_seconds,
            end_seconds=rc.end_seconds,
            embedding=emb,
        )
        db.add(k_chunk)
        db.flush()

        # Link junction table for citation resolution
        for seq, seg_id in enumerate(rc.segment_ids):
            db.add(
                KnowledgeChunkSegment(
                    tenant_id=current_user.organization_id,
                    chunk_id=k_chunk.id,
                    segment_id=seg_id,
                    sequence_in_chunk=seq,
                )
            )

        created_chunks.append(k_chunk)

    db.commit()

    retrieval_service = HybridRetrievalService(db=db, tenant_id=current_user.organization_id)
    response_items = []
    for c in created_chunks:
        citations = retrieval_service._resolve_citations(c.id)
        response_items.append(
            KnowledgeChunkResponse(
                id=c.id,
                meeting_id=c.meeting_id,
                transcript_id=c.transcript_id,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
                primary_topic=c.primary_topic,
                topic_tags=c.topic_tags,
                speaker_names=c.speaker_names,
                start_seconds=c.start_seconds,
                end_seconds=c.end_seconds,
                created_at=c.created_at,
                citations=citations,
            )
        )
    return response_items


@router.get(
    "/knowledge/search",
    response_model=HybridSearchResponse,
    summary="Perform hybrid retrieval (vector similarity + keyword FTS + RRF reranking) with citations",
)
def search_knowledge(
    q: str = Query(..., description="Search query string"),
    limit: int = Query(10, ge=1, le=50),
    meeting_id: Optional[UUID] = Query(None, description="Optional meeting filter"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
):
    service = HybridRetrievalService(db=db, tenant_id=current_user.organization_id)
    return service.hybrid_search(query=q, limit=limit, meeting_id=meeting_id)
