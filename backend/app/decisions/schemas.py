"""
Phase 17 – Decision Intelligence Pydantic v2 Schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DecisionEvidenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    segment_id: uuid.UUID
    snippet: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime


class DecisionTopicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    topic_name: str
    relevance_score: float = 1.0


class DecisionRelationshipSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_decision_id: uuid.UUID
    target_decision_id: uuid.UUID
    relationship_type: str
    confidence_score: float = 1.0
    reasoning: Optional[str] = None
    created_at: datetime


class DecisionEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    event_type: str
    previous_state: Optional[dict] = None
    new_state: Optional[dict] = None
    created_at: datetime


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: uuid.UUID
    intelligence_run_id: Optional[uuid.UUID] = None
    title: str
    description: str
    rationale: Optional[str] = None
    status: str
    impact_level: str
    decided_by_raw: Optional[str] = None
    decided_by_user_id: Optional[uuid.UUID] = None
    evidence_segment_ids: List[uuid.UUID] = Field(default_factory=list)
    effective_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    evidence_items: List[DecisionEvidenceSchema] = Field(default_factory=list)
    topics: List[DecisionTopicSchema] = Field(default_factory=list)
    outgoing_relationships: List[DecisionRelationshipSchema] = Field(default_factory=list)
    incoming_relationships: List[DecisionRelationshipSchema] = Field(default_factory=list)


class DecisionListResponse(BaseModel):
    items: List[DecisionResponse]
    total: int


class DecisionCreateRequest(BaseModel):
    title: str
    description: str
    rationale: Optional[str] = None
    impact_level: str = "MEDIUM"
    decided_by_raw: Optional[str] = None
    decided_by_user_id: Optional[uuid.UUID] = None
    evidence_segment_ids: List[uuid.UUID] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    effective_date: Optional[datetime] = None


class DecisionRelationshipCreate(BaseModel):
    target_decision_id: uuid.UUID
    relationship_type: str  # SUPERSEDES, REVERSES, REFINES, RELATED
    reasoning: Optional[str] = None
    confidence_score: float = 1.0


class DecisionGraphNode(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    impact_level: str
    created_at: datetime


class DecisionGraphEdge(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: str
    reasoning: Optional[str] = None


class DecisionGraphResponse(BaseModel):
    nodes: List[DecisionGraphNode]
    edges: List[DecisionGraphEdge]
