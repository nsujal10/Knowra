from typing import Protocol
from app.ai.diarization.schemas import DiarizationOptions, DiarizationResult


class DiarizationProvider(Protocol):
    def diarize(
        self,
        audio_path: str,
        options: DiarizationOptions,
    ) -> DiarizationResult:
        """
        Executes speaker diarization on the given audio file and returns a canonical DiarizationResult.
        """
        ...
