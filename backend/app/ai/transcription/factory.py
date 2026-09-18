from app.core.config import settings
from app.ai.transcription.interface import TranscriptionProvider

_provider_instance = None


def get_transcription_provider() -> TranscriptionProvider:
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_type = (getattr(settings, "ASR_PROVIDER", None) or os.getenv("ASR_PROVIDER") or "groq").lower().strip()

    if provider_type == "groq":
        from app.ai.transcription.providers.groq_whisper_provider import GroqWhisperProvider
        _provider_instance = GroqWhisperProvider()
    elif provider_type == "faster_whisper":
        from app.ai.transcription.providers.faster_whisper_provider import FasterWhisperProvider
        _provider_instance = FasterWhisperProvider()
    elif provider_type == "mock":
        from app.ai.transcription.providers.mock_provider import MockTranscriptionProvider
        _provider_instance = MockTranscriptionProvider()
    else:
        raise ValueError(f"Unknown ASR provider: {provider_type}")
        
    return _provider_instance