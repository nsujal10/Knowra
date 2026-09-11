from typing import Protocol
from app.ai.transcription.schemas import TranscriptionResult, TranscriptionOptions

class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: str, options: TranscriptionOptions) -> TranscriptionResult:
        """
        Executes ASR on the provided audio file and returns the canonical TranscriptionResult.
        """
        ...
