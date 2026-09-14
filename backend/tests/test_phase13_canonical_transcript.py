"""
Phase 13 – Canonical Transcript Test Suite

Tests cover:
  1. Mapper: provider output → CanonicalTranscript validation
  2. Validator: structural invariants (timestamps, confidence, sequence ordering)
  3. Service: get_canonical, create_edit_version (with DB mocking)
  4. API: GET /transcript, POST /transcript/versions, GET /transcript/versions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from pydantic import ValidationError

from app.transcript.schemas import (
    CanonicalTranscript,
    CanonicalSegment,
    CanonicalWord,
    TranscriptEditRequest,
    TranscriptEditResponse,
    TranscriptVersionMeta,
)
from app.transcript.validator import validate_segments, SegmentValidationError
from app.transcript.mapper import map_provider_output_to_canonical


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = uuid.uuid4()
MEETING_ID = uuid.uuid4()
TRANSCRIPT_ID = uuid.uuid4()


def _make_raw_output(
    segments: list | None = None,
    language: str = "en",
    duration: float = 30.0,
) -> Dict[str, Any]:
    if segments is None:
        segments = [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world.",
                "confidence": 0.95,
                "words": [
                    {"start": 0.0, "end": 2.0, "word": "Hello", "probability": 0.97},
                    {"start": 2.1, "end": 5.0, "word": "world.", "probability": 0.93},
                ],
            },
            {
                "start": 5.5,
                "end": 12.0,
                "text": "How are you?",
                "confidence": 0.88,
            },
        ]
    return {
        "language": language,
        "duration_seconds": duration,
        "provider_name": "faster-whisper",
        "model_name": "large-v3",
        "model_version": "1.0.0",
        "segments": segments,
    }


# ---------------------------------------------------------------------------
# Mapper tests
# ---------------------------------------------------------------------------

class TestMapper:
    def test_basic_mapping(self):
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, _make_raw_output()
        )
        assert isinstance(result, CanonicalTranscript)
        assert result.language == "en"
        assert result.duration_seconds == 30.0
        assert result.provider_name == "faster-whisper"
        assert len(result.segments) == 2

    def test_words_are_mapped(self):
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, _make_raw_output()
        )
        seg0 = result.segments[0]
        assert len(seg0.words) == 2
        assert seg0.words[0].text == "Hello"
        assert seg0.words[1].text == "world."

    def test_confidence_clamped_none(self):
        raw = _make_raw_output(
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello.", "confidence": None}
            ]
        )
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw
        )
        assert result.segments[0].confidence == 0.0

    def test_confidence_clamped_over_one(self):
        raw = _make_raw_output(
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello.", "confidence": 1.5}
            ]
        )
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw
        )
        assert result.segments[0].confidence == 1.0

    def test_invalid_segment_skipped(self):
        raw = _make_raw_output(
            segments=[
                {"start": 5.0, "end": 2.0, "text": "Bad.", "confidence": 0.9},  # end < start
                {"start": 0.0, "end": 5.0, "text": "Good.", "confidence": 0.9},
            ]
        )
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw
        )
        assert len(result.segments) == 1
        assert result.segments[0].text == "Good."

    def test_blank_segment_skipped(self):
        raw = _make_raw_output(
            segments=[
                {"start": 0.0, "end": 5.0, "text": "   ", "confidence": 0.9},
                {"start": 5.0, "end": 10.0, "text": "Valid.", "confidence": 0.9},
            ]
        )
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw
        )
        assert len(result.segments) == 1
        assert result.segments[0].text == "Valid."

    def test_zero_duration_raises(self):
        raw = _make_raw_output(duration=0.0)
        with pytest.raises(ValueError, match="duration_seconds"):
            map_provider_output_to_canonical(TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw)

    def test_negative_duration_raises(self):
        raw = _make_raw_output(duration=-5.0)
        with pytest.raises(ValueError, match="duration_seconds"):
            map_provider_output_to_canonical(TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw)

    def test_language_fallback(self):
        raw = _make_raw_output()
        raw["language"] = None
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, raw
        )
        assert result.language == "und"

    def test_ids_are_unique_per_segment(self):
        result = map_provider_output_to_canonical(
            TRANSCRIPT_ID, MEETING_ID, TENANT_ID, _make_raw_output()
        )
        ids = [str(s.id) for s in result.segments]
        assert len(ids) == len(set(ids)), "Segment IDs must be unique"


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

def _make_segment(
    seq: int = 0,
    start: float = 0.0,
    end: float = 5.0,
    text: str = "Hello.",
    confidence: float = 0.9,
) -> CanonicalSegment:
    return CanonicalSegment(
        id=uuid.uuid4(),
        sequence_number=seq,
        start_seconds=start,
        end_seconds=end,
        text=text,
        confidence=confidence,
    )


class TestValidator:
    def test_valid_segments_pass(self):
        segs = [_make_segment(0, 0.0, 5.0), _make_segment(1, 5.5, 10.0)]
        validate_segments(segs)  # should not raise

    def test_duplicate_sequence_numbers_raise(self):
        segs = [_make_segment(0), _make_segment(0)]
        with pytest.raises(SegmentValidationError, match="Duplicate sequence_number"):
            validate_segments(segs)

    def test_non_monotonic_sequence_raises(self):
        segs = [_make_segment(1), _make_segment(0)]
        with pytest.raises(SegmentValidationError, match="monotonically"):
            validate_segments(segs)

    def test_end_before_start_raises(self):
        # Pydantic v2 raises ValidationError at construction time because
        # CanonicalSegment has a @field_validator for end_seconds.
        with pytest.raises((ValidationError, SegmentValidationError)):
            segs = [_make_segment(0, start=5.0, end=2.0)]
            validate_segments(segs)

    def test_blank_text_raises(self):
        with pytest.raises(SegmentValidationError, match="blank"):
            # Pydantic's min_length=1 won't reject whitespace-only strings so
            # we pass a single space and rely on our custom validator stripping it.
            segs = [_make_segment(0, text="   ")]
            validate_segments(segs)

    def test_confidence_out_of_range_raises(self):
        # Pydantic v2 raises ValidationError if ge/le validators fire at construction;
        # our custom validator raises SegmentValidationError – catch either.
        with pytest.raises((ValidationError, SegmentValidationError)):
            segs = [_make_segment(0, confidence=1.5)]
            validate_segments(segs)

    def test_negative_start_raises(self):
        with pytest.raises((ValidationError, SegmentValidationError)):
            segs = [_make_segment(0, start=-1.0, end=5.0)]
            validate_segments(segs)

    def test_empty_list_is_valid(self):
        validate_segments([])  # should not raise


# ---------------------------------------------------------------------------
# Pydantic schema validation tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_transcript_edit_request_valid(self):
        req = TranscriptEditRequest(
            edit_reason="Fixed speaker attribution",
            segment_corrections={str(uuid.uuid4()): "Corrected text here."},
        )
        assert req.edit_reason == "Fixed speaker attribution"

    def test_transcript_edit_request_empty_reason_raises(self):
        with pytest.raises(ValidationError):
            TranscriptEditRequest(edit_reason="", segment_corrections={})

    def test_canonical_word_end_before_start_raises(self):
        with pytest.raises(ValidationError):
            CanonicalWord(
                id=uuid.uuid4(),
                sequence_number=0,
                start_seconds=5.0,
                end_seconds=2.0,
                text="bad",
                confidence=0.9,
            )

    def test_canonical_transcript_from_dict(self):
        data = {
            "id": str(uuid.uuid4()),
            "meeting_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "language": "en",
            "duration_seconds": 120.0,
            "provider_name": "faster-whisper",
            "model_name": "large-v3",
            "model_version": "1.0",
            "current_version_number": 1,
            "segments": [],
        }
        ct = CanonicalTranscript.model_validate(data)
        assert ct.language == "en"
        assert ct.duration_seconds == 120.0


# ---------------------------------------------------------------------------
# Service tests (using mocks)
# ---------------------------------------------------------------------------

class TestCanonicalTranscriptService:
    """Unit tests for CanonicalTranscriptService with mocked DB."""

    def _make_mock_word(self, seq: int = 0) -> MagicMock:
        w = MagicMock()
        w.id = uuid.uuid4()
        w.sequence_number = seq
        w.start_seconds = float(seq)
        w.end_seconds = float(seq) + 0.5
        w.text = f"word{seq}"
        w.confidence = 0.9
        return w

    def _make_mock_segment(self, seq: int = 0) -> MagicMock:
        seg = MagicMock()
        seg.id = uuid.uuid4()
        seg.sequence_number = seq
        seg.start_seconds = float(seq * 5)
        seg.end_seconds = float(seq * 5 + 4)
        seg.text = f"Segment {seq} text."
        seg.confidence = 0.95
        seg.speaker_id = None
        seg.speaker = None
        seg.alignment_confidence = None
        seg.alignment_status = None
        seg.words = [self._make_mock_word(0)]
        return seg

    def _make_mock_transcript(self) -> MagicMock:
        t = MagicMock()
        t.id = TRANSCRIPT_ID
        t.meeting_id = MEETING_ID
        t.tenant_id = TENANT_ID
        t.language = "en"
        t.duration_seconds = 30.0
        t.provider_name = "faster-whisper"
        t.model_name = "large-v3"
        t.model_version = "1.0"
        t.segments = [self._make_mock_segment(0), self._make_mock_segment(1)]
        return t

    def test_get_canonical_builds_from_rows(self):
        from app.transcript.service import CanonicalTranscriptService

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = self._make_mock_transcript()

        service = CanonicalTranscriptService(db=mock_db, tenant_id=TENANT_ID)
        result = service.get_canonical(meeting_id=MEETING_ID)

        assert isinstance(result, CanonicalTranscript)
        assert result.meeting_id == MEETING_ID
        assert len(result.segments) == 2

    def test_get_canonical_not_found_raises(self):
        from app.transcript.service import (
            CanonicalTranscriptService,
            TranscriptNotFoundError,
        )

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        service = CanonicalTranscriptService(db=mock_db, tenant_id=TENANT_ID)
        with pytest.raises(TranscriptNotFoundError):
            service.get_canonical(meeting_id=MEETING_ID)
