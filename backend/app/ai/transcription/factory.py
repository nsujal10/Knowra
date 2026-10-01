import os
from typing import Optional
from app.core.config import settings
from app.ai.transcription.interface import TranscriptionProvider


def get_transcription_provider(model: Optional[str] = None) -> TranscriptionProvider:
    """Create a transcription provider instance.

    * ``model`` – Optional model name to override the provider’s default.
      If ``None`` the provider will use its built‑in default (e.g. the
      ``GROQ_WHISPER_MODEL`` environment variable or the fallback "whisper-large-v3").
    * No global singleton is used – each call returns a fresh instance,
      allowing different parts of the system (upload vs live) to select
      different models safely.
    """
    provider_type = (
        getattr(settings, "ASR_PROVIDER", None)
        or os.getenv("ASR_PROVIDER")
        or "groq"
    ).lower().strip()

    if provider_type == "groq":
        from app.ai.transcription.providers.groq_whisper_provider import GroqWhisperProvider
        return GroqWhisperProvider(model=model or "")
    elif provider_type == "faster_whisper":
        from app.ai.transcription.providers.faster_whisper_provider import FasterWhisperProvider
        return FasterWhisperProvider()
    elif provider_type == "mock":
        from app.ai.transcription.providers.mock_provider import MockTranscriptionProvider
        return MockTranscriptionProvider()
    else:
        raise ValueError(f"Unknown ASR provider: {provider_type}")