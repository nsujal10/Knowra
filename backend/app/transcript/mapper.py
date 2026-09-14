"""
Phase 13 – Canonical Transcript Mapper

Ingests raw provider output from an ASR provider (e.g. faster-whisper or mock)
and converts it to the canonical CanonicalTranscript Pydantic schema.

Design rules
------------
- No semantic text rewriting (no spell-checking, no punctuation injection).
- Timestamps are preserved at full float precision.
- Missing or None confidence values default to 0.0 (safe floor).
- Missing word-level data is handled gracefully; an empty list is returned.
- The mapper NEVER writes to the database; it only produces validated schemas.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog

from app.transcript.schemas import (
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWord,
)
from app.transcript.validator import validate_segments, SegmentValidationError

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Raw provider output types (provider-agnostic dictionaries)
# ---------------------------------------------------------------------------
# Providers must supply data in the following dictionary shape.
# This avoids hard-coupling to any specific provider SDK.
#
#  RawProviderOutput = {
#      "language": str,
#      "duration_seconds": float,
#      "provider_name": str,
#      "model_name": str,
#      "model_version": str,
#      "segments": [
#          {
#              "start": float,
#              "end": float,
#              "text": str,
#              "confidence": float | None,   # optional
#              "words": [                     # optional
#                  {
#                      "start": float,
#                      "end": float,
#                      "word": str,
#                      "probability": float | None,
#                  }
#              ],
#          }
#      ],
#  }


def _safe_confidence(value: Any, fallback: float = 0.0) -> float:
    """Return a float confidence clamped to [0, 1]; use fallback on None/error."""
    try:
        v = float(value)
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return fallback


def _map_word(raw: Dict[str, Any], seq: int) -> Optional[CanonicalWord]:
    """
    Map a single raw word dict to CanonicalWord.
    Returns None if the word is invalid so callers can skip gracefully.
    """
    try:
        start = float(raw.get("start", 0.0))
        end = float(raw.get("end", 0.0))
        # faster-whisper uses "word", AssemblyAI uses "text"
        text = str(raw.get("word") or raw.get("text") or "").strip()
        if not text or end <= start:
            return None
        confidence = _safe_confidence(
            raw.get("probability") or raw.get("confidence")
        )
        return CanonicalWord(
            id=uuid.uuid4(),
            sequence_number=seq,
            start_seconds=start,
            end_seconds=end,
            text=text,
            confidence=confidence,
        )
    except Exception as exc:
        logger.warning("Skipping malformed word in provider output", error=str(exc))
        return None


def _map_segment(raw: Dict[str, Any], seq: int) -> Optional[CanonicalSegment]:
    """
    Map a single raw segment dict to CanonicalSegment.
    Returns None if the segment is structurally invalid so callers can skip.
    """
    try:
        start = float(raw.get("start", 0.0))
        end = float(raw.get("end", 0.0))
        text = str(raw.get("text") or "").strip()
        if not text or end <= start:
            logger.warning(
                "Skipping invalid segment",
                seq=seq,
                start=start,
                end=end,
                text_len=len(text),
            )
            return None
        confidence = _safe_confidence(raw.get("confidence") or raw.get("avg_logprob"))

        words: List[CanonicalWord] = []
        for w_idx, raw_word in enumerate(raw.get("words") or []):
            w = _map_word(raw_word, w_idx)
            if w is not None:
                words.append(w)

        return CanonicalSegment(
            id=uuid.uuid4(),
            sequence_number=seq,
            start_seconds=start,
            end_seconds=end,
            text=text,
            confidence=confidence,
            words=words,
        )
    except Exception as exc:
        logger.warning("Skipping malformed segment in provider output", error=str(exc))
        return None


def map_provider_output_to_canonical(
    transcript_id: uuid.UUID,
    meeting_id: uuid.UUID,
    tenant_id: uuid.UUID,
    raw: Dict[str, Any],
) -> CanonicalTranscript:
    """
    Primary adapter entry-point.

    Parameters
    ----------
    transcript_id : UUID of the parent Transcript DB row.
    meeting_id    : UUID of the meeting.
    tenant_id     : UUID of the owning tenant.
    raw           : Dict matching RawProviderOutput shape documented above.

    Returns
    -------
    CanonicalTranscript – fully validated Pydantic model.

    Raises
    ------
    SegmentValidationError if the mapped segments fail invariant checks.
    ValueError if required top-level fields are missing.
    """
    language = str(raw.get("language") or "und").strip() or "und"
    duration = float(raw.get("duration_seconds") or 0.0)
    provider_name = str(raw.get("provider_name") or "unknown")
    model_name = str(raw.get("model_name") or "unknown")
    model_version = str(raw.get("model_version") or "unknown")

    if duration <= 0:
        raise ValueError(
            f"duration_seconds must be > 0, got {duration}"
        )

    raw_segments: List[Dict[str, Any]] = raw.get("segments") or []
    mapped: List[CanonicalSegment] = []
    for idx, raw_seg in enumerate(raw_segments):
        seg = _map_segment(raw_seg, idx)
        if seg is not None:
            mapped.append(seg)

    # Validate invariants across the full segment list
    validate_segments(mapped)

    logger.info(
        "Mapped provider output to canonical transcript",
        transcript_id=str(transcript_id),
        segments_mapped=len(mapped),
        segments_skipped=len(raw_segments) - len(mapped),
    )

    return CanonicalTranscript(
        id=transcript_id,
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        language=language,
        duration_seconds=duration,
        provider_name=provider_name,
        model_name=model_name,
        model_version=model_version,
        current_version_number=1,
        segments=mapped,
    )
