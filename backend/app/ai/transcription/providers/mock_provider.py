from app.ai.transcription.interface import TranscriptionProvider
from app.ai.transcription.schemas import (
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptSegmentResult,
    TranscriptWordResult,
)


class MockTranscriptionProvider(TranscriptionProvider):
    def transcribe(
        self,
        audio_path: str,
        options: TranscriptionOptions,
    ) -> TranscriptionResult:

        return TranscriptionResult(
            language="en",
            duration=2.0,
            model_name="mock",
            model_version="1.0",
            segments=[
                TranscriptSegmentResult(
                    start_seconds=0.0,
                    end_seconds=1.0,
                    text="Hello world",
                    confidence=0.99,
                    words=[
                        TranscriptWordResult(
                            start_seconds=0.0,
                            end_seconds=0.5,
                            text="Hello",
                            confidence=0.99,
                        ),
                        TranscriptWordResult(
                            start_seconds=0.5,
                            end_seconds=1.0,
                            text="world",
                            confidence=0.99,
                        ),
                    ],
                )
            ],
        )