"""
Phase 23 – Cross-Meeting Intelligence Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TimelineEvent(BaseModel):
    """Represents a single chronological milestone or occurrence across meetings."""
    event_id: UUID = Field(..., description="Unique ID of the event/artifact")
    meeting_id: UUID = Field(..., description="Parent meeting UUID")
    meeting_title: str = Field(..., description="Human-readable meeting title")
    meeting_date: Optional[datetime] = Field(None, description="Recorded date of the meeting")
    timestamp_seconds: float = Field(0.0, description="Offset in seconds within the meeting audio/video")
    event_type: str = Field(..., description="TOPIC | DECISION | ACTION | TRANSCRIPT_MOMENT")
    title: str = Field(..., description="Headline of the event")
    description: str = Field(..., description="Detailed contextual description")
    speaker_name: Optional[str] = Field(None, description="Attributed speaker if known")
    status: Optional[str] = Field(None, description="Current lifecycle status (CONFIRMED, SUPERSEDED, OPEN, etc.)")
    evidence_segment_ids: List[UUID] = Field(default_factory=list, description="Canonical transcript segment IDs")
    quote: Optional[str] = Field(None, description="Verbatim transcript excerpt")


class TimelineResponse(BaseModel):
    """Aggregate chronological timeline across meetings."""
    entity_or_topic: str
    total_events: int
    meetings_covered: int
    events: List[TimelineEvent] = Field(default_factory=list)


class SubQueryTask(BaseModel):
    """Individual atomic sub-query spawned by query decomposition."""
    task_id: str
    query_type: str = Field(..., description="SEMANTIC_TOPIC | DECISION_HISTORY | ACTION_ITEMS | GRAPH_RELATIONSHIP")
    sub_query: str
    entity_focus: Optional[str] = None


class DecomposedQueryPlan(BaseModel):
    """Plan breaking down a complex multi-meeting question into sub-queries."""
    original_query: str
    intent: str
    requires_cross_meeting: bool
    tasks: List[SubQueryTask] = Field(default_factory=list)


class DecisionEvolutionNode(BaseModel):
    """Node in a decision's longitudinal lifecycle / supersession chain."""
    decision_id: UUID
    meeting_id: UUID
    meeting_title: str
    meeting_date: Optional[datetime] = None
    title: str
    description: str
    status: str
    relationship_type: Optional[str] = None  # ORIGINAL | SUPERSEDES | REVERSES | REFINES
    related_decision_id: Optional[UUID] = None
    evidence_segment_ids: List[UUID] = Field(default_factory=list)


class DecisionEvolutionResponse(BaseModel):
    """Complete evolutionary tree for an enterprise decision."""
    root_decision_id: UUID
    total_versions: int
    current_active_decision_id: Optional[UUID] = None
    evolution_chain: List[DecisionEvolutionNode] = Field(default_factory=list)


class CrossMeetingQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    entity_or_topic: Optional[str] = None
    meeting_ids: Optional[List[UUID]] = None
    limit_events: int = Field(20, ge=1, le=100)
