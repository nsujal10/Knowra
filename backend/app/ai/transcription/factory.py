import os

from app.ai.transcription.interface import TranscriptionProvider

_provider_instance = None


def get_transcription_provider() -> TranscriptionProvider:
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_type = os.getenv("ASR_PROVIDER", "faster_whisper")

    if provider_type == "faster_whisper":
        from app.ai.transcription.providers.faster_whisper_provider import FasterWhisperProvider
        _provider_instance = FasterWhisperProvider()
    elif provider_type == "mock":
        from app.ai.transcription.providers.mock_provider import MockTranscriptionProvider
        _provider_instance = MockTranscriptionProvider()
    else:
        raise ValueError(f"Unknown ASR provider: {provider_type}")
        
    return _provider_instance