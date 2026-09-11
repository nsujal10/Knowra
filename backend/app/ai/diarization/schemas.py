from pydantic import BaseModel, Field
from typing import List, Optional


class DiarizationOptions(BaseModel):
    num_speakers: Optional[int] = None
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None


class DiarizationSegment(BaseModel):
    speaker_label: str
    start_seconds: float
    end_seconds: float
    confidence: float = 1.0


class DiarizationResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    segments: List[DiarizationSegment] = Field(default_factory=list)
    speakers: List[str] = Field(default_factory=list)
    model_name: str
    model_version: str
