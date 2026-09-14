"""
Phase 15 & 16 – LLM Protocol & Structural Output Models (Pydantic v2)
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Structural Extraction Output Schemas
# ---------------------------------------------------------------------------

class LLMTopicOutput(BaseModel):
    title: str = Field(..., description="Concise headline of the discussion topic")
    summary: str = Field(..., description="2-3 sentence overview of what was discussed")
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    importance_score: float = Field(0.7, ge=0.0, le=1.0)
    evidence_segment_ids: List[UUID] = Field(
        default_factory=list,
        description="Exact segment IDs in the transcript supporting this topic",
    )


class LLMDecisionOutput(BaseModel):
    description: str = Field(..., description="Actionable summary of the decision reached")
    rationale: Optional[str] = Field(None, description="Why this decision was made")
    impact_level: str = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    decided_by_raw: Optional[str] = Field(None, description="Name or speaker label of the decision maker")
    evidence_segment_ids: List[UUID] = Field(
        default_factory=list,
        description="Exact segment IDs in the transcript containing the decision",
    )


class LLMRiskOutput(BaseModel):
    description: str = Field(..., description="Identified risk, blocker, or vulnerability")
    severity: str = Field("MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")
    mitigation: Optional[str] = Field(None, description="Proposed mitigation strategy discussed")
    status: str = Field("IDENTIFIED", description="IDENTIFIED | MITIGATED | ACCEPTED")
    evidence_segment_ids: List[UUID] = Field(
        default_factory=list,
        description="Exact segment IDs in the transcript detailing this risk",
    )


class LLMQuestionOutput(BaseModel):
    question_text: str = Field(..., description="The query raised during discussion")
    asked_by_raw: Optional[str] = Field(None, description="Name or speaker label of the asker")
    is_answered: bool = Field(False, description="Whether the question was resolved in meeting")
    answer_text: Optional[str] = Field(None, description="Summary of the answer provided")
    evidence_segment_ids: List[UUID] = Field(
        default_factory=list,
        description="Exact segment IDs where the question and answer occurred",
    )


class LLMCommitmentOutput(BaseModel):
    statement: str = Field(..., description="Explicit commitment made by an individual")
    made_by_raw: Optional[str] = Field(None, description="Name or speaker label of the person pledging")
    evidence_segment_ids: List[UUID] = Field(
        default_factory=list,
        description="Exact segment IDs containing the commitment",
    )


class LLMActionItemOutput(BaseModel):
    title: str = Field(..., description="Imperative task title, e.g., 'Deploy API service'")
    description: Optional[str] = Field(None, description="Additional context or acceptance criteria")
    priority: str = Field("MEDIUM", description="LOW | MEDIUM | HIGH | URGENT")
    raw_due_date_text: Optional[str] = Field(None, description="Original timeframe phrase, e.g. 'by next Friday'")
    raw_owner_text: Optional[str] = Field(None, description="Spoken owner phrase, e.g. 'David Miller', 'SPEAKER_00'")
    confidence: float = Field(0.85, ge=0.0, le=1.0)
    evidence_segment_ids: List[UUID] = Field(
        default_factory=list,
        description="Exact segment IDs where the task was assigned or agreed to",
    )


class LLMIntelligenceBundle(BaseModel):
    """Aggregate bundle returned by the LLM extraction pipeline."""
    topics: List[LLMTopicOutput] = Field(default_factory=list)
    decisions: List[LLMDecisionOutput] = Field(default_factory=list)
    risks: List[LLMRiskOutput] = Field(default_factory=list)
    questions: List[LLMQuestionOutput] = Field(default_factory=list)
    commitments: List[LLMCommitmentOutput] = Field(default_factory=list)
    action_items: List[LLMActionItemOutput] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


# ---------------------------------------------------------------------------
# LLM Provider Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for LLM extraction backends."""

    def extract_intelligence(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> LLMIntelligenceBundle:
        """Extract all meeting intelligence categories and action items."""
        ...

    def extract_action_items(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> List[LLMActionItemOutput]:
        """Extract dedicated action items from dialogue context."""
        ...
