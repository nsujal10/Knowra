from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class TranscriptWordSchema(BaseModel):
    start: float
    end: float
    text: str
    confidence: float

class TranscriptSegmentSchema(BaseModel):
    start: float
    end: float
    text: str
    confidence: float
    words: List[TranscriptWordSchema]

class TranscriptResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    language: str
    duration: float
    segments: List[TranscriptSegmentSchema]
