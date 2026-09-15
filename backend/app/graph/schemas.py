"""
Phase 24 – Organizational Knowledge Graph Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    canonical_name: str
    entity_type: str
    aliases: List[str] = Field(default_factory=list)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RelationshipSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    source_name: Optional[str] = None
    target_name: Optional[str] = None
    relationship_type: str
    confidence: float = 1.0
    meeting_id: Optional[UUID] = None
    evidence_segment_id: Optional[UUID] = None
    quote: Optional[str] = None


class SubGraphResponse(BaseModel):
    root_entity: EntitySchema
    depth: int = 1
    nodes: List[EntitySchema] = Field(default_factory=list)
    edges: List[RelationshipSchema] = Field(default_factory=list)


class EntitySearchResponse(BaseModel):
    total: int
    entities: List[EntitySchema] = Field(default_factory=list)


class GraphExtractionResponse(BaseModel):
    meeting_id: UUID
    entities_created: int
    relationships_created: int
    evidence_links_count: int
