"""
Phase 18 – Knowledge Chunking & Retrieval Schemas (Pydantic v2)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CitationSegmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_id: uuid.UUID
    start_seconds: float
    end_seconds: float
    speaker_name: Optional[str] = None
    text: str


class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    transcript_id: uuid.UUID
    chunk_index: int
    content: str
    token_count: int
    primary_topic: Optional[str] = None
    topic_tags: List[str] = Field(default_factory=list)
    speaker_names: List[str] = Field(default_factory=list)
    start_seconds: float
    end_seconds: float
    created_at: datetime
    citations: List[CitationSegmentSchema] = Field(default_factory=list)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    meeting_id: uuid.UUID
    content: str
    primary_topic: Optional[str] = None
    start_seconds: float
    end_seconds: float
    score: float
    vector_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    citations: List[CitationSegmentSchema] = Field(default_factory=list)


class HybridSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
