from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.ai.diarization.schemas import DiarizationSegment


class AlignmentStatus(str, Enum):
    ATTRIBUTED = "ATTRIBUTED"
    AMBIGUOUS = "AMBIGUOUS"
    OVERLAPPING = "OVERLAPPING"
    UNATTRIBUTED = "UNATTRIBUTED"


class SegmentAlignmentResult(BaseModel):
    speaker_label: Optional[str] = None
    alignment_confidence: float = 0.0
    alignment_status: str = AlignmentStatus.UNATTRIBUTED.value
    overlap_ratio: float = 0.0
    speaker_breakdown: Dict[str, float] = Field(default_factory=dict)


class TemporalAlignmentEngine:
    """
    Computes temporal intersection over ASR duration to attribute
    spoken transcript segments to diarized speaker timelines.
    """

    def __init__(
        self,
        min_attributed_threshold: float = 0.5,
        overlapping_threshold: float = 0.3,
        ambiguity_margin: float = 0.15,
    ):
        self.min_attributed_threshold = min_attributed_threshold
        self.overlapping_threshold = overlapping_threshold
        self.ambiguity_margin = ambiguity_margin

    def align_segment(
        self,
        asr_start: float,
        asr_end: float,
        diarization_segments: List[DiarizationSegment],
    ) -> SegmentAlignmentResult:
        asr_duration = max(asr_end - asr_start, 1e-6)

        # 1. Calculate temporal intersection for each speaker
        speaker_overlaps: Dict[str, float] = {}
        for spk_seg in diarization_segments:
            overlap = max(
                0.0,
                min(asr_end, spk_seg.end_seconds) - max(asr_start, spk_seg.start_seconds),
            )
            if overlap > 0.0:
                speaker_overlaps[spk_seg.speaker_label] = (
                    speaker_overlaps.get(spk_seg.speaker_label, 0.0) + overlap
                )

        if not speaker_overlaps:
            return SegmentAlignmentResult(
                speaker_label=None,
                alignment_confidence=0.0,
                alignment_status=AlignmentStatus.UNATTRIBUTED.value,
                overlap_ratio=0.0,
                speaker_breakdown={},
            )

        # 2. Compute overlap ratios
        speaker_ratios = {
            label: round(duration / asr_duration, 4)
            for label, duration in speaker_overlaps.items()
        }

        # Sort speakers by overlap ratio descending
        sorted_speakers = sorted(
            speaker_ratios.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        dominant_speaker, dominant_ratio = sorted_speakers[0]
        secondary_ratio = sorted_speakers[1][1] if len(sorted_speakers) > 1 else 0.0

        # Calculate simultaneous cross-talk (mutual overlap between top speakers within ASR bounds)
        mutual_overlap = 0.0
        if len(sorted_speakers) > 1:
            sec_speaker = sorted_speakers[1][0]
            dom_segs = [s for s in diarization_segments if s.speaker_label == dominant_speaker]
            sec_segs = [s for s in diarization_segments if s.speaker_label == sec_speaker]
            for d in dom_segs:
                for s in sec_segs:
                    start_bound = max(asr_start, d.start_seconds, s.start_seconds)
                    end_bound = min(asr_end, d.end_seconds, s.end_seconds)
                    if end_bound > start_bound:
                        mutual_overlap += (end_bound - start_bound)

        simultaneous_overlap_ratio = mutual_overlap / asr_duration

        # 3. Determine alignment state
        # State A: OVERLAPPING - multiple speakers talking at the same time
        if (
            simultaneous_overlap_ratio >= 0.1
            and dominant_ratio >= self.overlapping_threshold
            and secondary_ratio >= self.overlapping_threshold
        ):
            status = AlignmentStatus.OVERLAPPING.value
            confidence = min(1.0, dominant_ratio)

        # State B: ATTRIBUTED - dominant speaker meets attribution threshold and outpaces secondary
        elif (
            dominant_ratio >= self.min_attributed_threshold
            and (dominant_ratio - secondary_ratio) >= self.ambiguity_margin
        ):
            status = AlignmentStatus.ATTRIBUTED.value
            confidence = min(1.0, dominant_ratio)

        # State C: UNATTRIBUTED - overlap is negligible (< 10%)
        elif dominant_ratio < 0.1:
            status = AlignmentStatus.UNATTRIBUTED.value
            dominant_speaker = None
            confidence = 0.0

        # State D: AMBIGUOUS - split overlap or below confidence thresholds
        else:
            status = AlignmentStatus.AMBIGUOUS.value
            confidence = min(1.0, dominant_ratio)

        return SegmentAlignmentResult(
            speaker_label=dominant_speaker,
            alignment_confidence=round(confidence, 3),
            alignment_status=status,
            overlap_ratio=dominant_ratio,
            speaker_breakdown=speaker_ratios,
        )
