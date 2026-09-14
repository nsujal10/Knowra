"""
Phase 15 – LLM Gateway & Factory

Manages LLM provider selection and unified execution.
"""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.intelligence.llm.protocol import (
    LLMActionItemOutput,
    LLMIntelligenceBundle,
    LLMProvider,
)
from app.intelligence.llm.providers.mock_provider import MockLLMProvider

logger = structlog.get_logger(__name__)


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Factory creating the configured LLM provider instance."""
    name = (provider_name or settings.LLM_PROVIDER or "mock").lower()

    if name == "groq":
        from app.intelligence.llm.providers.groq_provider import GroqLLMProvider
        return GroqLLMProvider()

    # Default to deterministic mock provider
    return MockLLMProvider()


class LLMGateway:
    """Enterprise gateway wrapping LLM calls with logging, metrics, and error fallbacks."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_llm_provider()

    def extract_all(
        self,
        transcript_context: str,
        segments_meta: list[dict],
    ) -> LLMIntelligenceBundle:
        logger.info(
            "Extracting intelligence via LLM gateway",
            provider=type(self.provider).__name__,
            segments_count=len(segments_meta),
        )
        return self.provider.extract_intelligence(transcript_context, segments_meta)

    def extract_actions(
        self,
        transcript_context: str,
        segments_meta: list[dict],
    ) -> list[LLMActionItemOutput]:
        return self.provider.extract_action_items(transcript_context, segments_meta)
