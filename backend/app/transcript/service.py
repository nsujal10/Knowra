"""
Phase 13 – Canonical Transcript Service

Handles:
  1. Building the canonical view (assembling DB rows into CanonicalTranscript).
  2. Creating human-edit versions (versioning workflow with immutable AI baseline).
  3. Snapshot persistence (storing full canonical JSON to transcript_versions table).

Tenant isolation
----------------
All DB queries carry an explicit tenant_id filter.  The service NEVER accepts
a tenant_id from the request body; it receives it exclusively from TenantContext
which derives it from the server-verified JWT.
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from sqlalchemy.orm import Session, selectinload

from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.models.transcript_version import TranscriptVersion
from app.transcript.schemas import (
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWord,
    TranscriptVersionMeta,
    TranscriptEditRequest,
)
from app.transcript.validator import validate_segments, SegmentValidationError

logger = structlog.get_logger(__name__)


class TranscriptNotFoundError(Exception):
    pass


class TranscriptVersioningError(Exception):
    pass


class CanonicalTranscriptService:
    def __init__(self, db: Session, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Public: build canonical view
    # ------------------------------------------------------------------

    def get_canonical(
        self,
        meeting_id: uuid.UUID,
        version_number: Optional[int] = None,
    ) -> CanonicalTranscript:
        """
        Return the canonical transcript for a meeting.

        If version_number is None, returns the latest version built from
        live DB rows.  If version_number is specified, the snapshot stored
        in transcript_versions is returned verbatim (immutable provenance).
        """
        transcript = self._get_transcript(meeting_id)

        if version_number is not None:
            return self._load_version_snapshot(transcript, version_number)

        return self._build_canonical_from_rows(transcript)

    # ------------------------------------------------------------------
    # Public: create a human-edit version
    # ------------------------------------------------------------------

    def create_edit_version(
        self,
        meeting_id: uuid.UUID,
        editor_user_id: uuid.UUID,
        request: TranscriptEditRequest,
    ) -> int:
        """
        Apply text corrections and persist a new versioned snapshot.

        Rules
        -----
        - Timestamps are NEVER modified here (they stay from the AI run).
        - Only the text field of specified segments is corrected.
        - The original AI version (version_number=1) is immutable.
        - Returns the new version_number.
        """
        transcript = self._get_transcript(meeting_id)

        # Build current canonical state to snapshot
        current = self._build_canonical_from_rows(transcript)

        # Apply corrections
        corrected_segments = []
        corrections = request.segment_corrections
        for seg in current.segments:
            seg_id_str = str(seg.id)
            if seg_id_str in corrections:
                new_text = corrections[seg_id_str].strip()
                if not new_text:
                    raise SegmentValidationError(
                        f"Corrected text for segment {seg_id_str} must not be blank"
                    )
                corrected_segments.append(seg.model_copy(update={"text": new_text}))
            else:
                corrected_segments.append(seg)

        validate_segments(corrected_segments)

        # Determine next version number
        latest_version = (
            self.db.query(TranscriptVersion)
            .filter(
                TranscriptVersion.transcript_id == transcript.id,
                TranscriptVersion.tenant_id == self.tenant_id,
            )
            .order_by(TranscriptVersion.version_number.desc())
            .first()
        )
        next_number = (latest_version.version_number + 1) if latest_version else 2

        # Protect original AI version from being overwritten by ensuring at
        # least one existing version exists (seeded during transcript creation).
        if not latest_version:
            raise TranscriptVersioningError(
                "No baseline AI version found. "
                "Ensure the AI-generated snapshot was created during transcript ingest."
            )

        new_snapshot = current.model_copy(
            update={
                "current_version_number": next_number,
                "segments": corrected_segments,
            }
        )

        version_row = TranscriptVersion(
            tenant_id=self.tenant_id,
            transcript_id=transcript.id,
            version_number=next_number,
            source="HUMAN_EDITED",
            edited_by_user_id=editor_user_id,
            edit_reason=request.edit_reason,
            snapshot_json=new_snapshot.model_dump(mode="json"),
        )
        self.db.add(version_row)
        self.db.commit()

        logger.info(
            "Human edit version created",
            transcript_id=str(transcript.id),
            version=next_number,
            corrections_applied=len(corrections),
        )
        return next_number

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_transcript(self, meeting_id: uuid.UUID) -> Transcript:
        transcript = (
            self.db.query(Transcript)
            .options(
                selectinload(Transcript.segments).selectinload(TranscriptSegment.words),
                selectinload(Transcript.segments).selectinload(TranscriptSegment.speaker),
            )
            .filter(
                Transcript.meeting_id == meeting_id,
                Transcript.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not transcript:
            raise TranscriptNotFoundError(
                f"Transcript not found for meeting {meeting_id} "
                f"in tenant {self.tenant_id}"
            )
        return transcript

    def _build_canonical_from_rows(self, transcript: Transcript) -> CanonicalTranscript:
        """Assemble live DB rows into the canonical schema."""
        canonical_segs = []
        for seg in transcript.segments:
            canonical_words = [
                CanonicalWord(
                    id=w.id,
                    sequence_number=w.sequence_number,
                    start_seconds=w.start_seconds,
                    end_seconds=w.end_seconds,
                    text=w.text,
                    confidence=w.confidence,
                )
                for w in seg.words
            ]
            canonical_segs.append(
                CanonicalSegment(
                    id=seg.id,
                    sequence_number=seg.sequence_number,
                    start_seconds=seg.start_seconds,
                    end_seconds=seg.end_seconds,
                    text=seg.text,
                    confidence=seg.confidence,
                    speaker_id=seg.speaker_id,
                    speaker_label=seg.speaker.speaker_label if seg.speaker else None,
                    speaker_display_name=seg.speaker.display_name if seg.speaker else None,
                    alignment_confidence=seg.alignment_confidence,
                    alignment_status=seg.alignment_status,
                    words=canonical_words,
                )
            )

        return CanonicalTranscript(
            id=transcript.id,
            meeting_id=transcript.meeting_id,
            tenant_id=transcript.tenant_id,
            language=transcript.language,
            duration_seconds=transcript.duration_seconds,
            provider_name=transcript.provider_name,
            model_name=transcript.model_name,
            model_version=transcript.model_version,
            current_version_number=1,
            segments=canonical_segs,
        )

    def _load_version_snapshot(
        self,
        transcript: Transcript,
        version_number: int,
    ) -> CanonicalTranscript:
        """Retrieve an immutable version snapshot from the versions table."""
        version = (
            self.db.query(TranscriptVersion)
            .filter(
                TranscriptVersion.transcript_id == transcript.id,
                TranscriptVersion.version_number == version_number,
                TranscriptVersion.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not version:
            raise TranscriptNotFoundError(
                f"Version {version_number} not found for transcript {transcript.id}"
            )
        return CanonicalTranscript.model_validate(version.snapshot_json)
