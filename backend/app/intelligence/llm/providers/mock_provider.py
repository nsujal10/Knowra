"""
Phase 15 – Deterministic Mock LLM Provider

Extracts structured meeting intelligence from canonical segments without external network calls.
Used for offline testing, CI/CD, and deterministic pipeline validation.
"""

from __future__ import annotations

import re
from typing import List, Optional
from uuid import UUID, uuid4

import structlog

from app.intelligence.llm.protocol import (
    LLMActionItemOutput,
    LLMCommitmentOutput,
    LLMDecisionOutput,
    LLMIntelligenceBundle,
    LLMProvider,
    LLMQuestionOutput,
    LLMRiskOutput,
    LLMTopicOutput,
)

logger = structlog.get_logger(__name__)


class MockLLMProvider(LLMProvider):
    """
    Deterministic structural extractor that parses semantic markers
    or extracts sensible meeting artifacts from canonical segments.
    """

    def __init__(self, simulate_hallucination: bool = False) -> None:
        self.simulate_hallucination = simulate_hallucination

    def extract_intelligence(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> LLMIntelligenceBundle:
        """
        Analyze segments and produce a complete intelligence bundle.
        Uses actual segment UUIDs as evidence anchors.
        """
        if not segments_meta:
            return LLMIntelligenceBundle()

        first_seg_id = UUID(str(segments_meta[0]["id"]))
        last_seg_id = UUID(str(segments_meta[-1]["id"]))
        all_ids = [UUID(str(s["id"])) for s in segments_meta]

        # Extract Topics
        topics = [
            LLMTopicOutput(
                title="Strategic Quarterly Review & Integration Progress",
                summary="The executive team reviewed quarterly performance metrics and confirmed the customer intelligence platform rollout.",
                start_seconds=segments_meta[0].get("start_seconds", 0.0),
                end_seconds=segments_meta[-1].get("end_seconds", 10.0),
                importance_score=0.92,
                evidence_segment_ids=[first_seg_id, last_seg_id],
            )
        ]

        # Extract Decisions
        decisions = [
            LLMDecisionOutput(
                description="Approve Q2 customer intelligence integration roadmap.",
                rationale="Performance metrics exceeded expectations and timeline milestones are on schedule.",
                impact_level="HIGH",
                decided_by_raw=segments_meta[0].get("speaker_display_name") or "Executive Committee",
                evidence_segment_ids=[first_seg_id],
            )
        ]

        # Extract Risks
        risks = [
            LLMRiskOutput(
                description="Potential deployment schedule bottleneck across microservices.",
                severity="MEDIUM",
                mitigation="Stagger service rollouts and perform pre-release security validation.",
                status="IDENTIFIED",
                evidence_segment_ids=[last_seg_id],
            )
        ]

        # Extract Questions
        questions = [
            LLMQuestionOutput(
                question_text="Are customer intelligence integration milestones on schedule?",
                asked_by_raw=segments_meta[0].get("speaker_display_name") or "David Miller",
                is_answered=True,
                answer_text="Confirmed on schedule with no blocking dependencies.",
                evidence_segment_ids=[first_seg_id, last_seg_id],
            )
        ]

        # Extract Commitments
        commitments = [
            LLMCommitmentOutput(
                statement="Deliver final integration review by end of week.",
                made_by_raw=segments_meta[-1].get("speaker_display_name") or "Zira Vance",
                evidence_segment_ids=[last_seg_id],
            )
        ]

        # Extract Action Items
        action_items = self.extract_action_items(transcript_context, segments_meta)

        if self.simulate_hallucination:
            # Inject an invalid non-existent segment ID for testing the gate
            decisions[0].evidence_segment_ids.append(uuid4())

        return LLMIntelligenceBundle(
            topics=topics,
            decisions=decisions,
            risks=risks,
            questions=questions,
            commitments=commitments,
            action_items=action_items,
            prompt_tokens=420,
            completion_tokens=280,
        )

    def extract_action_items(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> List[LLMActionItemOutput]:
        """Extract concrete action items anchored to segments."""
        if not segments_meta:
            return []

        first_seg_id = UUID(str(segments_meta[0]["id"]))
        last_seg_id = UUID(str(segments_meta[-1]["id"]))
        speaker0_name = segments_meta[0].get("speaker_display_name") or "David Miller"
        speaker1_name = segments_meta[-1].get("speaker_display_name") or "Zira Vance"

        items = [
            LLMActionItemOutput(
                title="Prepare quarterly executive dashboard report",
                description="Consolidate Q2 KPI metrics and prepare slides for leadership review.",
                priority="HIGH",
                raw_due_date_text="by next Friday",
                raw_owner_text=speaker0_name,
                confidence=0.95,
                evidence_segment_ids=[first_seg_id],
            ),
            LLMActionItemOutput(
                title="Complete customer intelligence integration validation",
                description="Run end-to-end regression tests on the new intelligence service endpoints.",
                priority="URGENT",
                raw_due_date_text="tomorrow at 5pm",
                raw_owner_text=speaker1_name,
                confidence=0.91,
                evidence_segment_ids=[last_seg_id],
            ),
        ]

        return items
