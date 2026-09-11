import json
from pydantic import BaseModel, Field
from typing import List, Optional
from app.media.ffmpeg.runner import run_command
from app.media.ffmpeg.errors import EmptyAudio

class FFProbeStream(BaseModel):
    index: int
    codec_type: str
    codec_name: Optional[str] = None
    sample_rate: Optional[str] = None
    channels: Optional[int] = None
    duration: Optional[str] = None
    
class FFProbeFormat(BaseModel):
    duration: Optional[str] = None
    format_name: Optional[str] = None
    size: Optional[str] = None

class FFProbeResult(BaseModel):
    streams: List[FFProbeStream] = Field(default_factory=list)
    format: FFProbeFormat

def probe_media(file_path: str, timeout: int = 60) -> FFProbeResult:
    """Extracts strongly-typed metadata from media file using ffprobe."""
    cmd = [
        "ffprobe", 
        "-v", "quiet", 
        "-print_format", "json",
        "-show_format", 
        "-show_streams", 
        file_path
    ]
    stdout, _ = run_command(cmd, timeout=timeout)
    
    try:
        data = json.loads(stdout)
        return FFProbeResult(**data)
    except Exception as e:
        raise ValueError(f"Failed to parse ffprobe output: {str(e)}")

def get_primary_audio_stream(probe_result: FFProbeResult) -> FFProbeStream:
    """Finds the first valid audio stream."""
    for stream in probe_result.streams:
        if stream.codec_type == "audio":
            return stream
    raise EmptyAudio("No audio streams found in media file.")
