"""
Phase 15 – Transcript Context Builder

Transforms CanonicalTranscript into a structured, LLM-ready context block
anchoring every utterance to its segment UUID, speaker attribution, and time range.
"""

from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from app.transcript.schemas import CanonicalSegment, CanonicalTranscript


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS.cc"""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


class ContextBuilder:
    """Builds chunked or complete prompt context from CanonicalTranscript."""

    def __init__(self, max_tokens: int = 16000) -> None:
        self.max_tokens = max_tokens

    def build_context(
        self,
        transcript: CanonicalTranscript,
    ) -> Tuple[str, List[dict]]:
        """
        Produce:
          1. Formatted dialogue string with embedded segment metadata
          2. Machine-readable list of segment metadata dictionaries
        """
        lines: List[str] = [
            f"=== MEETING TRANSCRIPT (Meeting ID: {transcript.meeting_id}) ===",
            f"Language: {transcript.language} | Total Duration: {transcript.duration_seconds:.2f}s | Segments: {len(transcript.segments)}",
            "",
            "--- DIALOGUE LOG ---",
        ]

        segments_meta: List[dict] = []

        for seg in transcript.segments:
            speaker_label = seg.speaker_display_name or seg.speaker_label or "Unknown Speaker"
            start_str = format_seconds(seg.start_seconds)
            end_str = format_seconds(seg.end_seconds)

            line = f"[Segment ID: {seg.id} | {start_str} -> {end_str} | Speaker: {speaker_label}]\n{seg.text}\n"
            lines.append(line)

            segments_meta.append({
                "id": seg.id,
                "sequence_number": seg.sequence_number,
                "speaker_id": seg.speaker_id,
                "speaker_label": seg.speaker_label,
                "speaker_display_name": seg.speaker_display_name,
                "start_seconds": seg.start_seconds,
                "end_seconds": seg.end_seconds,
                "text": seg.text,
            })

        lines.append("=== END OF TRANSCRIPT ===")
        context_str = "\n".join(lines)
        return context_str, segments_meta
