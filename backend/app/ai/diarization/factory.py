import os
from typing import Optional
from app.ai.diarization.interface import DiarizationProvider

_provider_instance: Optional[DiarizationProvider] = None


def get_diarization_provider() -> DiarizationProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_type = os.getenv("DIARIZATION_PROVIDER", "pyannote").lower()

    if provider_type == "pyannote":
        from app.ai.diarization.providers.pyannote_provider import PyannoteProvider
        _provider_instance = PyannoteProvider()
    elif provider_type == "mock":
        from app.ai.diarization.providers.mock_provider import MockDiarizationProvider
        _provider_instance = MockDiarizationProvider()
    else:
        raise ValueError(f"Unknown diarization provider: {provider_type}")

    return _provider_instance


def reset_provider_instance():
    """Helper for test suites to inject or reset the singleton provider."""
    global _provider_instance
    _provider_instance = None
