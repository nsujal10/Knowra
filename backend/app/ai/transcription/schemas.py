from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class TranscriptionOptions(BaseModel):
    language: Optional[str] = None
    beam_size: int = 5
    vad_filter: bool = True
    vad_parameters: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 250,
            "threshold": 0.5,
        }
    )
    condition_on_previous_text: bool = False
    temperature: Union[float, List[float]] = Field(
        default_factory=lambda: [0.0, 0.2, 0.4, 0.6, 0.8]
    )
    no_speech_threshold: float = 0.6
    initial_prompt: Optional[str] = None
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

