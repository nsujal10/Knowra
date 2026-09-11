from app.media.ffmpeg.probe import probe_media, get_primary_audio_stream
from app.media.ffmpeg.errors import EmptyAudio, CorruptedAudio
import structlog

logger = structlog.get_logger(__name__)

def validate_audio(file_path: str) -> float:
    """
    Validates audio streams and returns the reliable duration.
    Throws EmptyAudio or CorruptedAudio on failure.
    """
    try:
        probe = probe_media(file_path)
        stream = get_primary_audio_stream(probe)
        
        # Prefer stream duration, fallback to format duration
        duration_str = stream.duration or probe.format.duration
        if not duration_str:
            raise CorruptedAudio("Could not determine media duration.")
            
        duration = float(duration_str)
        if duration < 0.5:
            raise EmptyAudio("Audio duration is less than 0.5 seconds.")
            
        return duration
    except EmptyAudio:
        raise
    except Exception as e:
        logger.error("Audio validation failed", error=str(e))
        raise CorruptedAudio(f"Audio validation failed: {str(e)}")
