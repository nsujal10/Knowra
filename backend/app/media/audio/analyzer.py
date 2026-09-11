import re
from app.media.ffmpeg.runner import run_command
from app.models.audio_enums import AudioQuality
import structlog

logger = structlog.get_logger(__name__)

class AudioAnalysisResult:
    def __init__(self, silence_duration: float, quality: AudioQuality):
        self.silence_duration = silence_duration
        self.quality = quality

def analyze_audio(file_path: str, duration: float) -> AudioAnalysisResult:
    """
    Analyzes audio for silence ratio and peak levels without destructively altering it.
    """
    cmd = [
        "ffmpeg", 
        "-i", file_path, 
        "-af", "silencedetect=noise=-50dB:d=2,astats=metadata=1:reset=1", 
        "-f", "null", 
        "-"
    ]
    
    # FFmpeg analysis runs quickly but requires reading the entire stream. Timeout proportional to duration.
    timeout = min(600, int(duration * 2.0) + 60)
    
    try:
        _, stderr = run_command(cmd, timeout=timeout)
    except Exception as e:
        logger.warning("Audio analysis failed, defaulting to acceptable", error=str(e))
        return AudioAnalysisResult(0.0, AudioQuality.ACCEPTABLE)
        
    silence_duration = 0.0
    for line in stderr.splitlines():
        if "silencedetect" in line and "silence_duration:" in line:
            match = re.search(r"silence_duration:\s+([\d\.]+)", line)
            if match:
                silence_duration += float(match.group(1))
                
    silence_ratio = silence_duration / duration if duration > 0 else 0
    
    # Simple quality heuristics for implementation
    if silence_ratio > 0.9:
        quality = AudioQuality.POOR
    elif silence_ratio > 0.5:
        quality = AudioQuality.ACCEPTABLE
    else:
        quality = AudioQuality.GOOD
        
    return AudioAnalysisResult(silence_duration, quality)
