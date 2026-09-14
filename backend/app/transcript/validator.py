"""
Phase 13 – Canonical Transcript Validator

Enforces structural invariants before any segment is persisted or published.
Raises ValueError with a clear message so callers can return 422 responses.
"""

from __future__ import annotations

from typing import List

from app.transcript.schemas import CanonicalSegment, CanonicalWord


class SegmentValidationError(ValueError):
    """Raised when a segment violates canonical invariants."""


def validate_word(word: CanonicalWord, segment_idx: int) -> None:
    """Validate a single word-level token."""
    if word.start_seconds < 0:
        raise SegmentValidationError(
            f"Segment[{segment_idx}] word '{word.text}': start_seconds must be >= 0"
            f" (got {word.start_seconds})"
        )
    if word.end_seconds <= word.start_seconds:
        raise SegmentValidationError(
            f"Segment[{segment_idx}] word '{word.text}': "
            f"end_seconds ({word.end_seconds}) must be > start_seconds ({word.start_seconds})"
        )
    if not word.text.strip():
        raise SegmentValidationError(
            f"Segment[{segment_idx}]: word text must not be blank"
        )
    if not (0.0 <= word.confidence <= 1.0):
        raise SegmentValidationError(
            f"Segment[{segment_idx}] word '{word.text}': "
            f"confidence ({word.confidence}) must be in [0.0, 1.0]"
        )


def validate_segment(seg: CanonicalSegment, idx: int) -> None:
    """Validate a single transcript segment and its child words."""
    if seg.start_seconds < 0:
        raise SegmentValidationError(
            f"Segment[{idx}]: start_seconds must be >= 0 (got {seg.start_seconds})"
        )
    if seg.end_seconds <= seg.start_seconds:
        raise SegmentValidationError(
            f"Segment[{idx}]: end_seconds ({seg.end_seconds}) must be "
            f"> start_seconds ({seg.start_seconds})"
        )
    if not seg.text.strip():
        raise SegmentValidationError(
            f"Segment[{idx}]: text must not be blank"
        )
    if not (0.0 <= seg.confidence <= 1.0):
        raise SegmentValidationError(
            f"Segment[{idx}]: confidence ({seg.confidence}) must be in [0.0, 1.0]"
        )
    for word in seg.words:
        validate_word(word, idx)


def validate_segments(segments: List[CanonicalSegment]) -> None:
    """
    Validate an ordered list of segments.

    Invariants
    ----------
    - Each segment passes individual validation (see validate_segment).
    - Sequence numbers are unique and monotonically increasing.
    - Segments must not have zero-length text after stripping whitespace.
    """
    seen_seq = set()
    for idx, seg in enumerate(segments):
        validate_segment(seg, idx)
        if seg.sequence_number in seen_seq:
            raise SegmentValidationError(
                f"Duplicate sequence_number {seg.sequence_number} at index {idx}"
            )
        seen_seq.add(seg.sequence_number)

    # Enforce monotonic ordering
    seq_list = [s.sequence_number for s in segments]
    if seq_list != sorted(seq_list):
        raise SegmentValidationError(
            "Segment sequence_numbers are not monotonically increasing"
        )
