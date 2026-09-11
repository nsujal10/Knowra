from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class DiarizationJobResponse(BaseModel):
    message: str
    job_id: str


class DiarizationStatusResponse(BaseModel):
    job_id: str
    status: str
    metadata: Optional[dict] = None


class SpeakerResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    speaker_label: str
    display_name: str
    user_id: Optional[UUID] = None


class SpeakerUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    user_id: Optional[UUID] = None


class DiarizedWordSchema(BaseModel):
    start: float
    end: float
    text: str
    confidence: float


class DiarizedSegmentSchema(BaseModel):
    id: UUID
    sequence_number: int
    start: float
    end: float
    text: str
    confidence: float
    speaker_id: Optional[UUID] = None
    speaker_label: Optional[str] = None
    speaker_name: Optional[str] = None
    alignment_confidence: Optional[float] = None
    alignment_status: Optional[str] = None
    words: List[DiarizedWordSchema] = Field(default_factory=list)


class DiarizedTranscriptResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    language: str
    duration: float
    segments: List[DiarizedSegmentSchema]
    speakers: List[SpeakerResponse]
