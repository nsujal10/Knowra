"""
Phase 15 – Groq / OpenAI-Compatible LLM Provider

Supports Groq Cloud & OpenAI-compatible endpoints with structured JSON responses.
Uses httpx directly without vendor lock-in.
"""

from __future__ import annotations

import json
import os
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

import re
import time

SYSTEM_PROMPT = """You are an enterprise meeting intelligence extraction engine.
Analyze the provided meeting dialogue and extract structured intelligence across all dimensions.
You MUST anchor all extracted topics, decisions, action items, risks, questions, and commitments
to the EXACT segment IDs provided in the dialogue. Do not invent or hallucinate segment IDs.

MULTILINGUAL & HINDI LANGUAGE HANDLING:
- The dialogue may be in English, Hindi (Devanagari script), Hinglish (Hindi written in Roman/Latin script), or a bilingual mixture.
- Fully analyze Hindi utterances with the same depth as English. Do NOT discard, skip, or over-summarize Hindi speech.
- Deeply understand conversational Hindi markers:
  * Decisions (फैसले / निर्णय): e.g. "हमने तय किया है", "हम यह अप्रोच फॉलो करेंगे", "फाइनल किया गया".
  * Action items (कार्य / अगले कदम): e.g. "मैं कल तक पूरा कर दूंगा", "आप रिपोर्ट शेयर कर देना", "अगले हफ्ते रिव्यू करेंगे", "कर देना", "करना है", "चेक कर लेना", "बना देना".
  * Questions (सवाल): e.g. "क्या यह मुमकिन है?", "टाइमलाइन क्या है?".
  * Risks (जोखिम / आशंका): e.g. "इसमें लेट होने का रिस्क है", "डेटा लॉस हो सकता है".
- In the output JSON, write titles, summaries, and descriptions in clear, professional English while preserving any specific Hindi terms, project codenames, or nuances in parentheses or quotes where helpful.

CRITICAL INSTRUCTIONS:
1. "topics": Extract 2 to 3 key discussion themes directly grounded in dialogue. Keep summary concise (1-2 sentences).
2. "action_items": Extract all concrete action items, next steps, tasks, or follow-ups explicitly or implicitly discussed/assigned. Assign each to the appropriate speaker. If NO action items were discussed, return [].
3. "decisions": Extract agreed choices, ratifications, or strategic directions.
4. "commitments": Extract verbal commitments or promises made by participants.
5. "evidence_segment_ids": Provide 1 to 2 key segment IDs as evidence anchors.
6. If the transcript does not support a category, return an empty array for that field.

You MUST respond strictly with a valid JSON object matching this schema (do not include markdown fences or extraneous text):
{
  "topics": [{"title": "...", "summary": "...", "start_seconds": 0.0, "end_seconds": 5.0, "importance_score": 0.8, "evidence_segment_ids": ["uuid..."]}],
  "action_items": [{"title": "...", "description": "...", "priority": "HIGH", "raw_due_date_text": "by Friday", "raw_owner_text": "Speaker Name", "confidence": 0.9, "evidence_segment_ids": ["uuid..."]}],
  "decisions": [{"description": "...", "rationale": "...", "impact_level": "MEDIUM", "decided_by_raw": "...", "evidence_segment_ids": ["uuid..."]}],
  "commitments": [{"statement": "...", "made_by_raw": "...", "evidence_segment_ids": ["uuid..."]}],
  "risks": [{"description": "...", "severity": "MEDIUM", "mitigation": "...", "status": "IDENTIFIED", "evidence_segment_ids": ["uuid..."]}],
  "questions": [{"question_text": "...", "asked_by_raw": "...", "is_answered": true, "answer_text": "...", "evidence_segment_ids": ["uuid..."]}]
}
"""

ACTION_ITEMS_PROMPT = """You are an expert executive meeting assistant.
Analyze this meeting dialogue and extract ALL concrete action items, tasks, deliverables, commitments, and next steps discussed or agreed upon.
Look for tasks assigned to participants or commitments by participants to do work (e.g. review, deploy, test, prepare, send, complete, document, verify, follow up).

For each action item output:
- title: concise imperative task (e.g. 'Verify MinIO storage policies and metrics')
- description: brief context
- priority: HIGH, MEDIUM, or LOW
- raw_owner_text: person responsible (or speaker name) or null
- raw_due_date_text: timeline/deadline mentioned (e.g. 'by Friday', 'next week', 'tomorrow') or null
- confidence: 0.9
- evidence_segment_ids: 1 to 2 exact segment IDs from the dialogue

Respond strictly with valid JSON:
{
  "action_items": [
    {
      "title": "...",
      "description": "...",
      "priority": "HIGH",
      "raw_owner_text": "...",
      "raw_due_date_text": "...",
      "confidence": 0.9,
      "evidence_segment_ids": ["uuid..."]
    }
  ]
}"""


class GroqLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str = "",
        model: str = "qwen/qwen3.8-27b",
        base_url: str = "https://api.groq.com/openai/v1",
    ) -> None:
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = os.getenv("LLM_MODEL") or os.getenv("GROQ_MODEL") or getattr(settings, "LLM_MODEL", "qwen/qwen3.8-27b")
        self.base_url = base_url
        self.fallback_model = "openai/gpt-oss-20b"

    def _execute_chat_completion(self, payload: dict) -> dict:
        """Executes chat completion with retry and automatic model fallback on 429."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        current_model = payload.get("model", self.model)
        models_to_try = [current_model]
        if self.fallback_model != current_model:
            models_to_try.append(self.fallback_model)

        last_error = None
        for model_choice in models_to_try:
            req_payload = dict(payload)
            req_payload["model"] = model_choice

            for attempt in range(3):
                try:
                    with httpx.Client(timeout=45.0) as client:
                        res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=req_payload)
                        if res.status_code == 429:
                            retry_after = float(res.headers.get("retry-after", 2.0 * (attempt + 1)))
                            logger.warning(
                                "Groq rate limit 429 encountered",
                                model=model_choice,
                                retry_after=retry_after,
                                attempt=attempt,
                            )
                            if attempt < 2:
                                time.sleep(min(retry_after, 5.0))
                                continue
                            # If retries on this model fail with 429, break to next model choice
                            break

                        res.raise_for_status()
                        return res.json()
                except Exception as exc:
                    last_error = exc
                    logger.warning("Groq call failed, retrying", model=model_choice, error=str(exc))
                    time.sleep(1.0)

        if last_error:
            raise RuntimeError(f"All Groq LLM attempts failed: {last_error}") from last_error
        raise RuntimeError("Groq LLM returned empty response")

    @staticmethod
    def _parse_robust_json(s: str) -> dict:
        """Robust JSON extraction handling markdown fences, trailing commas, and truncation."""
        s = re.sub(r"^```(?:json)?\s*", "", s.strip(), flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
        match = re.search(r"(\{.*\})", s, re.DOTALL)
        raw = match.group(1) if match else s
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([\]}])", r"\1", raw)
            cleaned = re.sub(r"\}\s*\{", "}, {", cleaned)
            cleaned = re.sub(r"\]\s*\[", "], [", cleaned)
            cleaned = re.sub(r"\}\s*\n\s*\{", "},\n{", cleaned)
            cleaned = re.sub(r'(["\d\]}])\s*\n\s*"([a-zA-Z0-9_]+)"\s*:', r'\1,\n"\2":', cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # Truncation recovery: trim to last complete object and close brackets/braces
            last_brace = cleaned.rfind("}")
            if last_brace != -1:
                truncated = cleaned[:last_brace + 1]
                open_br = truncated.count("[") - truncated.count("]")
                open_bc = truncated.count("{") - truncated.count("}")
                truncated += ("]" * max(0, open_br)) + ("}" * max(0, open_bc))
                truncated = re.sub(r",\s*([\]}])", r"\1", truncated)
                try:
                    return json.loads(truncated)
                except json.JSONDecodeError:
                    pass

            return {}

    def extract_intelligence(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> LLMIntelligenceBundle:
        """Query LLM for full intelligence extraction."""
        if not self.api_key:
            raise ValueError("No LLM API key configured for GroqLLMProvider")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript_context},
            ],
            "temperature": 0.1,
            "max_tokens": 850,
        }

        data = self._execute_chat_completion(payload)
        content = data["choices"][0]["message"]["content"]
        parsed = self._parse_robust_json(content)
        usage = data.get("usage", {})

        action_items = [LLMActionItemOutput(**a) for a in parsed.get("action_items", []) if isinstance(a, dict) and a.get("title")]

        # If primary pass didn't extract any action items, run dedicated action extraction pass
        if not action_items:
            logger.info("Main intelligence extraction found 0 action items, running dedicated action pass")
            action_items = self.extract_action_items(transcript_context, segments_meta)

        return LLMIntelligenceBundle(
            topics=[LLMTopicOutput(**t) for t in parsed.get("topics", []) if isinstance(t, dict) and t.get("title")],
            decisions=[LLMDecisionOutput(**d) for d in parsed.get("decisions", []) if isinstance(d, dict) and d.get("description")],
            risks=[LLMRiskOutput(**r) for r in parsed.get("risks", []) if isinstance(r, dict) and r.get("description")],
            questions=[LLMQuestionOutput(**q) for q in parsed.get("questions", []) if isinstance(q, dict) and q.get("question_text")],
            commitments=[LLMCommitmentOutput(**c) for c in parsed.get("commitments", []) if isinstance(c, dict) and c.get("statement")],
            action_items=action_items,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def extract_action_items(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> List[LLMActionItemOutput]:
        """Dedicated focused extraction pass for action items."""
        if not self.api_key:
            return []

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ACTION_ITEMS_PROMPT},
                {"role": "user", "content": transcript_context},
            ],
            "temperature": 0.1,
            "max_tokens": 700,
        }

        try:
            data = self._execute_chat_completion(payload)
            if not data or "choices" not in data or not data["choices"]:
                return []
            content = data["choices"][0]["message"]["content"]
            parsed = self._parse_robust_json(content)
            raw_items = parsed.get("action_items", [])
            return [LLMActionItemOutput(**a) for a in raw_items if isinstance(a, dict) and a.get("title")]
        except Exception as exc:
            logger.warning("Dedicated action items extraction failed", error=str(exc))
            return []
