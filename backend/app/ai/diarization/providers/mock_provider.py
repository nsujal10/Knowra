from typing import List, Optional
from app.ai.diarization.interface import DiarizationProvider
from app.ai.diarization.postprocess import postprocess_diarization_segments
from app.ai.diarization.schemas import (
    DiarizationOptions,
    DiarizationResult,
    DiarizationSegment,
)


class MockDiarizationProvider(DiarizationProvider):
    def __init__(self, predefined_segments: Optional[List[DiarizationSegment]] = None):
        self.predefined_segments = predefined_segments

    def diarize(
        self,
        audio_path: str,
        options: DiarizationOptions,
    ) -> DiarizationResult:
        if self.predefined_segments is not None:
            segments = self.predefined_segments
        else:
            segments = [
                DiarizationSegment(
                    speaker_label="SPEAKER_00",
                    start_seconds=0.0,
                    end_seconds=1.0,
                    confidence=0.98,
                ),
                DiarizationSegment(
                    speaker_label="SPEAKER_00",
                    start_seconds=1.2,
                    end_seconds=2.0,
                    confidence=0.95,
                ),
                DiarizationSegment(
                    speaker_label="SPEAKER_01",
                    start_seconds=2.0,
                    end_seconds=3.5,
                    confidence=0.95,
                ),
            ]

        cleaned, unique_speakers = postprocess_diarization_segments(
            segments,
            gap_seconds=options.merge_gap_seconds,
        )

        return DiarizationResult(
            segments=cleaned,
            speakers=unique_speakers,
            model_name="mock-pyannote",
            model_version="1.0",
        )
