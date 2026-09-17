"""
Phase 13 – Canonical Transcript Schemas (Pydantic v2)

These models represent the *canonical* view of a transcript that the system
exposes to consumers.  They are strictly read-only from the consumer perspective;
any mutation must go through the versioning service which creates a new version row.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Word-level canonical unit
# ---------------------------------------------------------------------------

class CanonicalWord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_number: int
    start_seconds: float = Field(..., ge=0.0)
    end_seconds: float
    text: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("end_seconds")
    @classmethod
    def end_after_start(cls, v: float, info) -> float:
        start = info.data.get("start_seconds", 0.0)
        if v <= start:
            return round(start + 0.05, 3)
        return v


# ---------------------------------------------------------------------------
# Segment-level canonical unit
# ---------------------------------------------------------------------------

class CanonicalSegment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_number: int
    start_seconds: float = Field(..., ge=0.0)
    end_seconds: float
    text: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Speaker attribution – set after Phase 12 alignment
    speaker_id: Optional[UUID] = None
    speaker_label: Optional[str] = None
    speaker_display_name: Optional[str] = None
    alignment_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    alignment_status: Optional[str] = None

    words: List[CanonicalWord] = Field(default_factory=list)

    @field_validator("end_seconds")
    @classmethod
    def end_after_start(cls, v: float, info) -> float:
        start = info.data.get("start_seconds", 0.0)
        if v <= start:
            return round(start + 0.05, 3)
        return v


# ---------------------------------------------------------------------------
# Transcript version provenance metadata
# ---------------------------------------------------------------------------

class TranscriptVersionMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_number: int
    source: str  # "AI_GENERATED" | "HUMAN_EDITED"
    edited_by_user_id: Optional[UUID] = None
    edit_reason: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Top-level canonical transcript
# ---------------------------------------------------------------------------

class CanonicalTranscript(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meeting_id: UUID
    tenant_id: UUID
    language: str
    duration_seconds: float = Field(..., gt=0.0)
    provider_name: str
    model_name: str
    model_version: str

    # Version metadata – present when the caller requests a specific version
    current_version_number: int = 1
    version_meta: Optional[TranscriptVersionMeta] = None

    segments: List[CanonicalSegment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Input payload for creating a new human-edited version
# ---------------------------------------------------------------------------

class TranscriptEditRequest(BaseModel):
    """
    Payload submitted by a human editor.  Only text corrections are allowed
    (timestamps come from the original ASR; they must not be overridden here).
    """
    edit_reason: str = Field(..., min_length=1, max_length=1024)
    # Map of segment UUID → corrected text.  Only include changed segments.
    segment_corrections: dict[str, str] = Field(default_factory=dict)


class TranscriptEditResponse(BaseModel):
    transcript_id: UUID
    new_version_number: int
    message: str
