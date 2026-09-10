import subprocess
import structlog
import os

logger = structlog.get_logger(__name__)

def normalize_to_wav(input_path: str, output_path: str) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg normalization failed", stderr=e.stderr)
        return False
