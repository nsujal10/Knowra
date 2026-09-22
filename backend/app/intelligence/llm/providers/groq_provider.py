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
You MUST anchor all extracted topics, decisions, risks, questions, commitments, and action items
to the EXACT segment IDs provided in the dialogue. Do not invent or hallucinate segment IDs.

MULTILINGUAL & HINDI LANGUAGE HANDLING:
- The dialogue may be in English, Hindi (Devanagari script), Hinglish (Hindi written in Roman/Latin script), or a bilingual mixture.
- Fully analyze Hindi utterances with the same depth as English. Do NOT discard, skip, or over-summarize Hindi speech.
- Deeply understand conversational Hindi markers:
  * Decisions (फैसले / निर्णय): e.g. "हमने तय किया है", "हम यह अप्रोच फॉलो करेंगे", "फाइनल किया गया".
  * Action items (कार्य / अगले कदम): e.g. "मैं कल तक पूरा कर दूंगा", "आप रिपोर्ट शेयर कर देना", "अगले हफ्ते रिव्यू करेंगे".
  * Questions (सवाल): e.g. "क्या यह मुमकिन है?", "टाइमलाइन क्या है?".
  * Risks (जोखिम / आशंका): e.g. "इसमें लेट होने का रिस्क है", "डेटा लॉस हो सकता है".
- In the output JSON, write titles, summaries, and descriptions in clear, professional English while preserving any specific Hindi terms, project codenames, or nuances in parentheses or quotes where helpful.

CRITICAL INSTRUCTIONS:
1. "topics": Extract 2 to 4 key discussion points and overarching themes directly grounded in the dialogue.
2. "action_items": Extract concrete action items, next steps, or follow-ups explicitly discussed in the meeting. Assign each to the appropriate speaker. If NO action items were discussed, return an empty array ([]). Do NOT invent fictional tasks.
3. "evidence_segment_ids": Provide 1 to 3 key segment IDs as evidence anchors. NEVER output more than 3 segment IDs per item.
4. If the transcript does not support a category, return an empty array for that field.

You MUST respond strictly with a valid JSON object matching this schema (do not include markdown fences or extraneous text):
{
  "topics": [{"title": "...", "summary": "...", "start_seconds": 0.0, "end_seconds": 5.0, "importance_score": 0.8, "evidence_segment_ids": ["uuid..."]}],
  "decisions": [{"description": "...", "rationale": "...", "impact_level": "MEDIUM", "decided_by_raw": "...", "evidence_segment_ids": ["uuid..."]}],
  "risks": [{"description": "...", "severity": "MEDIUM", "mitigation": "...", "status": "IDENTIFIED", "evidence_segment_ids": ["uuid..."]}],
  "questions": [{"question_text": "...", "asked_by_raw": "...", "is_answered": true, "answer_text": "...", "evidence_segment_ids": ["uuid..."]}],
  "commitments": [{"statement": "...", "made_by_raw": "...", "evidence_segment_ids": ["uuid..."]}],
  "action_items": [{"title": "...", "description": "...", "priority": "HIGH", "raw_due_date_text": "by Friday", "raw_owner_text": "Speaker Name", "confidence": 0.9, "evidence_segment_ids": ["uuid..."]}]
}
"""


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

    def extract_intelligence(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> LLMIntelligenceBundle:
        """Query LLM for full intelligence extraction."""
        if not self.api_key:
            raise ValueError("No LLM API key configured for GroqLLMProvider")

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
            "temperature": 0.1,
            "max_tokens": 850,
        }

        data = None
        for attempt in range(5):
            try:
                with httpx.Client(timeout=60.0) as client:
                    res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                    if res.status_code == 429 and attempt < 4:
                        retry_after = float(res.headers.get("retry-after", 7.0 * (attempt + 1)))
                        logger.warning("Groq rate limit 429 encountered, backing off", retry_after=retry_after, attempt=attempt)
                        time.sleep(retry_after)
                        continue
                    res.raise_for_status()
                    data = res.json()
                    break
            except httpx.HTTPStatusError as err:
                if err.response.status_code == 429 and attempt < 4:
                    retry_after = float(err.response.headers.get("retry-after", 7.0 * (attempt + 1)))
                    logger.warning("Groq rate limit 429 HTTPStatusError, backing off", retry_after=retry_after, attempt=attempt)
                    time.sleep(retry_after)
                    continue
                logger.error("Groq extraction HTTP error", status=err.response.status_code, error=str(err))
                raise RuntimeError(f"Groq LLM extraction failed: {err}") from err
            except Exception as exc:
                logger.error("Groq extraction connection error", error=str(exc))
                raise RuntimeError(f"Groq LLM extraction failed: {exc}") from exc

        if not data or "choices" not in data or not data["choices"]:
            raise RuntimeError("Groq LLM returned empty or invalid response")

        content = data["choices"][0]["message"]["content"]
        # Robust JSON extraction handling optional markdown fences and minor syntax hiccups
        def _parse_robust_json(s: str) -> dict:
            # Strip markdown code blocks
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

                with open("raw_error_output.txt", "w", encoding="utf-8") as err_f:
                    err_f.write(raw)
                return json.loads(cleaned)

        parsed = _parse_robust_json(content)
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

    def extract_action_items(
        self,
        transcript_context: str,
        segments_meta: List[dict],
    ) -> List[LLMActionItemOutput]:
        bundle = self.extract_intelligence(transcript_context, segments_meta)
        return bundle.action_items
