from pydantic import BaseModel, Field
from typing import List, Optional

class TranscriptionOptions(BaseModel):
    language: Optional[str] = None
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = True

class TranscriptWordResult(BaseModel):
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float

class TranscriptSegmentResult(BaseModel):
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float
    words: List[TranscriptWordResult] = Field(default_factory=list)

class TranscriptionResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    language: str
    duration: float
    segments: List[TranscriptSegmentResult] = Field(default_factory=list)
    model_name: str
    model_version: str

