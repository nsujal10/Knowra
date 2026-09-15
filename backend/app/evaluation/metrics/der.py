"""
Phase 25 – Diarization Error Rate (DER) Evaluator

Calculates Missed Speech, False Alarm Speech, Speaker Confusion, and aggregate DER
comparing hypothesis speaker timelines against ground-truth reference speaker timelines.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


class DEREvaluator:
    """
    Computes Diarization Error Rate (DER).
    Formula:
        DER = (Missed + FalseAlarm + Confusion) / TotalReferenceDuration
    """

    def __init__(self, step_seconds: float = 0.1, collar_seconds: float = 0.0) -> None:
        self.step_seconds = step_seconds
        self.collar_seconds = collar_seconds

    def evaluate_der(
        self,
        reference_segments: List[Dict[str, any]],
        hypothesis_segments: List[Dict[str, any]],
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        Evaluates DER given lists of segments with keys: 'start', 'end', 'speaker'.
        If speaker_mapping is None, automatically computes optimal greedy speaker alignment.
        """
        if not reference_segments:
            return {
                "der": 0.0,
                "missed_speech_time": 0.0,
                "false_alarm_time": 0.0,
                "speaker_confusion_time": 0.0,
                "total_reference_time": 0.0,
            }

        max_time = max(
            max((s["end"] for s in reference_segments), default=0.0),
            max((s["end"] for s in hypothesis_segments), default=0.0),
        )

        if max_time <= 0.0:
            return {
                "der": 0.0,
                "missed_speech_time": 0.0,
                "false_alarm_time": 0.0,
                "speaker_confusion_time": 0.0,
                "total_reference_time": 0.0,
            }

        # Build speaker mapping if not provided (greedy overlap matching)
        if speaker_mapping is None:
            speaker_mapping = self._align_speakers(reference_segments, hypothesis_segments)

        # Discretize timeline
        num_frames = int(max_time / self.step_seconds) + 1
        ref_timeline: List[Optional[str]] = [None] * num_frames
        hyp_timeline: List[Optional[str]] = [None] * num_frames

        for s in reference_segments:
            st_idx = int(s["start"] / self.step_seconds)
            end_idx = min(int(s["end"] / self.step_seconds), num_frames - 1)
            for i in range(st_idx, end_idx + 1):
                ref_timeline[i] = str(s["speaker"])

        for s in hypothesis_segments:
            st_idx = int(s["start"] / self.step_seconds)
            end_idx = min(int(s["end"] / self.step_seconds), num_frames - 1)
            hyp_spk = speaker_mapping.get(str(s["speaker"]), str(s["speaker"]))
            for i in range(st_idx, end_idx + 1):
                hyp_timeline[i] = hyp_spk

        missed_frames = 0
        fa_frames = 0
        confusion_frames = 0
        total_ref_frames = 0

        for r, h in zip(ref_timeline, hyp_timeline):
            if r is not None:
                total_ref_frames += 1
                if h is None:
                    missed_frames += 1
                elif r != h:
                    confusion_frames += 1
            else:
                if h is not None:
                    fa_frames += 1

        total_ref_sec = total_ref_frames * self.step_seconds
        missed_sec = missed_frames * self.step_seconds
        fa_sec = fa_frames * self.step_seconds
        confusion_sec = confusion_frames * self.step_seconds

        der = (missed_sec + fa_sec + confusion_sec) / total_ref_sec if total_ref_sec > 0 else 0.0

        return {
            "der": round(der, 4),
            "missed_speech_time": round(missed_sec, 2),
            "false_alarm_time": round(fa_sec, 2),
            "speaker_confusion_time": round(confusion_sec, 2),
            "total_reference_time": round(total_ref_sec, 2),
        }

    def _align_speakers(
        self,
        reference_segments: List[Dict[str, any]],
        hypothesis_segments: List[Dict[str, any]],
    ) -> Dict[str, str]:
        """Greedily matches hypothesis speaker labels to reference speaker labels by temporal co-occurrence."""
        co_occurrence: Dict[Tuple[str, str], float] = {}

        for r in reference_segments:
            for h in hypothesis_segments:
                overlap = max(0.0, min(r["end"], h["end"]) - max(r["start"], h["start"]))
                if overlap > 0:
                    pair = (str(h["speaker"]), str(r["speaker"]))
                    co_occurrence[pair] = co_occurrence.get(pair, 0.0) + overlap

        mapping: Dict[str, str] = {}
        assigned_refs: Set[str] = set()

        sorted_pairs = sorted(co_occurrence.items(), key=lambda x: x[1], reverse=True)
        for (h_spk, r_spk), _ in sorted_pairs:
            if h_spk not in mapping and r_spk not in assigned_refs:
                mapping[h_spk] = r_spk
                assigned_refs.add(r_spk)

        return mapping
