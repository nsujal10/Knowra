"""
Phase 15 – Groq / OpenAI-Compatible LLM Provider

Supports Groq Cloud & OpenAI-compatible endpoints with structured JSON responses.
Uses httpx directly without vendor lock-in.
"""

from __future__ import annotations

import json
from typing import List
from uuid import UUID

import httpx
import structlog

from app.core.config import settings
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

SYSTEM_PROMPT = """You are an enterprise meeting intelligence extraction engine.
Analyze the provided meeting dialogue and extract structured intelligence.
You MUST anchor all extracted topics, decisions, risks, questions, commitments, and action items
to the EXACT segment_ids provided in the dialogue. Do not invent or hallucinate segment_ids.

Return your response strictly as valid JSON matching this schema:
{
  "topics": [{"title": "...", "summary": "...", "start_seconds": 0.0, "end_seconds": 5.0, "importance_score": 0.8, "evidence_segment_ids": ["uuid..."]}],
  "decisions": [{"description": "...", "rationale": "...", "impact_level": "MEDIUM", "decided_by_raw": "...", "evidence_segment_ids": ["uuid..."]}],
  "risks": [{"description": "...", "severity": "MEDIUM", "mitigation": "...", "status": "IDENTIFIED", "evidence_segment_ids": ["uuid..."]}],
  "questions": [{"question_text": "...", "asked_by_raw": "...", "is_answered": true, "answer_text": "...", "evidence_segment_ids": ["uuid..."]}],
  "commitments": [{"statement": "...", "made_by_raw": "...", "evidence_segment_ids": ["uuid..."]}],
  "action_items": [{"title": "...", "description": "...", "priority": "HIGH", "raw_due_date_text": "by Friday", "raw_owner_text": "Alice", "confidence": 0.9, "evidence_segment_ids": ["uuid..."]}]
}
"""


class GroqLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str = "",
        model: str = "llama3-70b-8192",
        base_url: str = "https://api.groq.com/openai/v1",
    ) -> None:
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url

    def extract_intelligence(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> LLMIntelligenceBundle:
        """Query LLM for full intelligence extraction."""
        if not self.api_key:
            logger.warning("No LLM API key configured; falling back to Mock provider")
            from app.intelligence.llm.providers.mock_provider import MockLLMProvider
            return MockLLMProvider().extract_intelligence(transcript_context, segments_meta)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript_context},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            usage = data.get("usage", {})

            return LLMIntelligenceBundle(
                topics=[LLMTopicOutput(**t) for t in parsed.get("topics", [])],
                decisions=[LLMDecisionOutput(**d) for d in parsed.get("decisions", [])],
                risks=[LLMRiskOutput(**r) for r in parsed.get("risks", [])],
                questions=[LLMQuestionOutput(**q) for q in parsed.get("questions", [])],
                commitments=[LLMCommitmentOutput(**c) for c in parsed.get("commitments", [])],
                action_items=[LLMActionItemOutput(**a) for a in parsed.get("action_items", [])],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )
        except Exception as exc:
            logger.error("Groq extraction failed, falling back to mock", error=str(exc))
            from app.intelligence.llm.providers.mock_provider import MockLLMProvider
            return MockLLMProvider().extract_intelligence(transcript_context, segments_meta)

    def extract_action_items(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> List[LLMActionItemOutput]:
        bundle = self.extract_intelligence(transcript_context, segments_meta)
        return bundle.action_items
