"""
Phase 15 – Meeting Intelligence Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TopicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    intelligence_run_id: UUID
    title: str
    summary: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    importance_score: float = Field(..., ge=0.0, le=1.0)
    evidence_segment_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime


class DecisionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    intelligence_run_id: UUID
    description: str
    rationale: Optional[str] = None
    impact_level: str = "MEDIUM"  # LOW | MEDIUM | HIGH
    decided_by_raw: Optional[str] = None
    decided_by_user_id: Optional[UUID] = None
    evidence_segment_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime


class RiskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    intelligence_run_id: UUID
    description: str
    severity: str = "MEDIUM"  # LOW | MEDIUM | HIGH | CRITICAL
    mitigation: Optional[str] = None
    status: str = "IDENTIFIED"
    evidence_segment_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime


class QuestionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    intelligence_run_id: UUID
    question_text: str
    asked_by_raw: Optional[str] = None
    asked_by_user_id: Optional[UUID] = None
    is_answered: bool = False
    answer_text: Optional[str] = None
    evidence_segment_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime


class CommitmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    intelligence_run_id: UUID
    statement: str
    made_by_raw: Optional[str] = None
    made_by_user_id: Optional[UUID] = None
    evidence_segment_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime


class IntelligenceRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    tenant_id: UUID
    transcript_version_number: int
    status: str
    provider_name: str
    model_name: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    idempotency_key: str
    created_at: datetime


class MeetingIntelligenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meeting_id: UUID
    intelligence_run: IntelligenceRunSchema
    topics: List[TopicSchema] = Field(default_factory=list)
    decisions: List[DecisionSchema] = Field(default_factory=list)
    risks: List[RiskSchema] = Field(default_factory=list)
    questions: List[QuestionSchema] = Field(default_factory=list)
    commitments: List[CommitmentSchema] = Field(default_factory=list)


class TriggerIntelligenceRequest(BaseModel):
    transcript_version_number: Optional[int] = Field(
        None,
        ge=1,
        description="Version to analyze. Defaults to latest canonical version.",
    )
    force: bool = Field(
        False,
        description="Bypass idempotency check and force a fresh analysis run.",
    )
