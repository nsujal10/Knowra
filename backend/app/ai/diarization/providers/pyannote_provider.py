import os
import structlog
from typing import Dict
from app.ai.diarization.interface import DiarizationProvider
from app.ai.diarization.schemas import (
    DiarizationOptions,
    DiarizationResult,
    DiarizationSegment,
)

logger = structlog.get_logger(__name__)


class PyannoteProvider(DiarizationProvider):
    def __init__(self):
        try:
            import torch
            from pyannote.audio import Pipeline
        except ImportError:
            raise ImportError(
                "pyannote.audio is not installed. Please install it with 'pip install pyannote.audio' to use PyannoteProvider."
            )

        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        self.model_name = os.getenv("DIARIZATION_MODEL_NAME", "pyannote/speaker-diarization-3.1")
        self.device = "cuda" if torch.cuda.is_available() and os.getenv("DIARIZATION_DEVICE", "cuda") == "cuda" else "cpu"

        logger.info(
            "Initializing Pyannote Diarization Pipeline",
            model_name=self.model_name,
            device=self.device,
        )

        self.pipeline = Pipeline.from_pretrained(
            self.model_name,
            use_auth_token=hf_token,
        )
        if self.pipeline is not None:
            self.pipeline.to(torch.device(self.device))

    def diarize(
        self,
        audio_path: str,
        options: DiarizationOptions,
    ) -> DiarizationResult:
        if self.pipeline is None:
            raise RuntimeError("Pyannote pipeline failed to initialize.")

        logger.info("Starting speaker diarization", audio_path=audio_path)

        # Build pipeline kwargs
        kwargs = {}
        if options.num_speakers is not None:
            kwargs["num_speakers"] = options.num_speakers
        if options.min_speakers is not None:
            kwargs["min_speakers"] = options.min_speakers
        if options.max_speakers is not None:
            kwargs["max_speakers"] = options.max_speakers

        diarization = self.pipeline(audio_path, **kwargs)

        # pyannote annotation iteration: (segment, track, speaker)
        raw_segments = []
        speaker_mapping: Dict[str, str] = {}
        speaker_counter = 0

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if speaker not in speaker_mapping:
                speaker_mapping[speaker] = f"SPEAKER_{speaker_counter:02d}"
                speaker_counter += 1

            normalized_label = speaker_mapping[speaker]
            raw_segments.append(
                DiarizationSegment(
                    speaker_label=normalized_label,
                    start_seconds=round(turn.start, 3),
                    end_seconds=round(turn.end, 3),
                    confidence=1.0,
                )
            )

        unique_speakers = sorted(list(speaker_mapping.values()))

        logger.info(
            "Diarization inference completed",
            segments_count=len(raw_segments),
            speakers_count=len(unique_speakers),
        )

        return DiarizationResult(
            segments=raw_segments,
            speakers=unique_speakers,
            model_name="pyannote.audio",
            model_version=self.model_name,
        )
