"""
Post-processing for speaker diarization segments.

Merges consecutive / near-adjacent same-speaker turns and remaps cluster
labels to stable, user-friendly Speaker A/B/... identities.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from app.ai.diarization.schemas import DiarizationSegment

# Gap (seconds) under which consecutive same-speaker turns are merged.
DEFAULT_MERGE_GAP_SECONDS = 0.5


def merge_adjacent_segments(
    segments: List[DiarizationSegment],
    gap_seconds: float = DEFAULT_MERGE_GAP_SECONDS,
) -> List[DiarizationSegment]:
    """
    Merge consecutive or highly overlapping segments that share a speaker label.

    Example: SPEAKER_01 ends at 12.5s and SPEAKER_01 starts at 12.8s → one segment.
    """
    if not segments:
        return []

    ordered = sorted(segments, key=lambda s: (s.start_seconds, s.end_seconds))
    merged: List[DiarizationSegment] = [ordered[0].model_copy(deep=True)]

    for seg in ordered[1:]:
        prev = merged[-1]
        same_speaker = prev.speaker_label == seg.speaker_label
        gap = seg.start_seconds - prev.end_seconds
        overlaps = seg.start_seconds <= prev.end_seconds

        if same_speaker and (overlaps or gap <= gap_seconds):
            prev.end_seconds = round(max(prev.end_seconds, seg.end_seconds), 3)
            prev.confidence = min(prev.confidence, seg.confidence)
        else:
            merged.append(seg.model_copy(deep=True))

    return merged


def remap_to_clean_labels(
    segments: List[DiarizationSegment],
) -> Tuple[List[DiarizationSegment], List[str]]:
    """
    Remap arbitrary cluster IDs to stable Speaker A, Speaker B, ... labels
    in first-appearance order across the timeline.
    """
    if not segments:
        return [], []

    label_map: Dict[str, str] = {}
    next_index = 0
    remapped: List[DiarizationSegment] = []

    for seg in segments:
        if seg.speaker_label not in label_map:
            letter = chr(ord("A") + next_index) if next_index < 26 else f"{next_index + 1}"
            label_map[seg.speaker_label] = f"Speaker {letter}"
            next_index += 1

        remapped.append(
            DiarizationSegment(
                speaker_label=label_map[seg.speaker_label],
                start_seconds=seg.start_seconds,
                end_seconds=seg.end_seconds,
                confidence=seg.confidence,
            )
        )

    speakers = list(dict.fromkeys(label_map.values()))
    return remapped, speakers


def postprocess_diarization_segments(
    segments: List[DiarizationSegment],
    gap_seconds: float = DEFAULT_MERGE_GAP_SECONDS,
) -> Tuple[List[DiarizationSegment], List[str]]:
    """Merge adjacent turns, then assign clean Speaker A/B labels."""
    merged = merge_adjacent_segments(segments, gap_seconds=gap_seconds)
    return remap_to_clean_labels(merged)
