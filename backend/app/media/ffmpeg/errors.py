class AudioProcessingError(Exception):
    """Base exception for audio processing pipeline."""
    pass

class DecodeFailure(AudioProcessingError):
    """Raised when FFmpeg/FFprobe fails to decode the media."""
    pass

class FFmpegTimeout(AudioProcessingError):
    """Raised when a subprocess exceeds the enforced timeout."""
    pass

class CorruptedAudio(AudioProcessingError):
    """Raised when the audio stream is detected as corrupted."""
    pass

class EmptyAudio(AudioProcessingError):
    """Raised when no audio streams are present."""
    pass
