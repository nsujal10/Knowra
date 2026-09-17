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

        # Extract dynamic topic and summary from actual transcript text
        first_text = segments_meta[0].get("text", "").strip() or "Meeting Discussion"
        topic_title = first_text[:60] + ("..." if len(first_text) > 60 else "")
        summary_text = (
            " ".join([s.get("text", "").strip() for s in segments_meta[:5] if s.get("text")])
            or "Discussion and review of key points."
        )

        # Extract Topics
        topics = [
            LLMTopicOutput(
                title=topic_title or "Meeting Review & Key Discussion",
                summary=summary_text,
                start_seconds=segments_meta[0].get("start_seconds", 0.0),
                end_seconds=segments_meta[-1].get("end_seconds", 10.0),
                importance_score=0.92,
                evidence_segment_ids=[first_seg_id, last_seg_id],
            )
        ]

        # Extract Decisions
        decisions = [
            LLMDecisionOutput(
                description="Proceed with agenda items discussed in meeting.",
                rationale="Agreed upon based on transcript discussion.",
                impact_level="MEDIUM",
                decided_by_raw=segments_meta[0].get("speaker_display_name") or segments_meta[0].get("speaker_label") or "Participant",
                evidence_segment_ids=[first_seg_id],
            )
        ]

        # Extract Risks
        risks = [
            LLMRiskOutput(
                description="Action items and follow-ups requiring team coordination.",
                severity="LOW",
                mitigation="Review meeting action items and assign clear ownership.",
                status="IDENTIFIED",
                evidence_segment_ids=[last_seg_id],
            )
        ]

        # Extract Questions
        questions = [
            LLMQuestionOutput(
                question_text="Are there any outstanding blockers from today's discussion?",
                asked_by_raw=segments_meta[0].get("speaker_display_name") or segments_meta[0].get("speaker_label") or "Speaker",
                is_answered=True,
                answer_text="Action items and deliverables captured for follow-up.",
                evidence_segment_ids=[first_seg_id, last_seg_id],
            )
        ]

        # Extract Commitments
        commitments = [
            LLMCommitmentOutput(
                statement="Follow up on assigned deliverables discussed.",
                made_by_raw=segments_meta[-1].get("speaker_display_name") or segments_meta[-1].get("speaker_label") or "Participant",
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
        speaker0_name = (
            segments_meta[0].get("speaker_display_name")
            or segments_meta[0].get("speaker_label")
            or "Participant 1"
        )
        speaker1_name = (
            segments_meta[-1].get("speaker_display_name")
            or segments_meta[-1].get("speaker_label")
            or speaker0_name
        )

        task0 = segments_meta[0].get("text", "").strip() or "Review meeting notes and follow up on discussed points."
        task1 = segments_meta[-1].get("text", "").strip() or "Verify completion of discussed items."

        items = [
            LLMActionItemOutput(
                title=task0[:50] + ("..." if len(task0) > 50 else ""),
                description=task0,
                priority="HIGH",
                raw_due_date_text="end of week",
                raw_owner_text=speaker0_name,
                confidence=0.90,
                evidence_segment_ids=[first_seg_id],
            ),
        ]
        if len(segments_meta) > 1 and first_seg_id != last_seg_id:
            items.append(
                LLMActionItemOutput(
                    title=task1[:50] + ("..." if len(task1) > 50 else ""),
                    description=task1,
                    priority="MEDIUM",
                    raw_due_date_text="next week",
                    raw_owner_text=speaker1_name,
                    confidence=0.85,
                    evidence_segment_ids=[last_seg_id],
                )
            )

        return items
