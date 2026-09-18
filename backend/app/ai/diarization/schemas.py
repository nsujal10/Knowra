from pydantic import BaseModel, Field
from typing import List, Optional


class DiarizationOptions(BaseModel):
    num_speakers: Optional[int] = None
    min_speakers: Optional[int] = 1
    max_speakers: Optional[int] = 10
    # Merge gap for consecutive same-speaker turns (seconds)
    merge_gap_seconds: float = 0.5


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
