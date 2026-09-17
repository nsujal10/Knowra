import subprocess
import structlog
import os
from typing import Optional

logger = structlog.get_logger(__name__)

def normalize_to_wav(input_path: str, output_path: str, duration_seconds: Optional[float] = None) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.warning("FFmpeg standard audio normalization failed, trying silent track fallback", stderr=e.stderr)
        try:
            dur = duration_seconds if (duration_seconds and duration_seconds > 0) else 5.0
            cmd_silent = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                "-t", str(dur),
                "-sample_fmt", "s16",
                output_path
            ]
            subprocess.run(cmd_silent, capture_output=True, text=True, check=True)
            logger.info("Generated silent fallback audio for video without audio stream", duration=dur)
            return True
        except subprocess.CalledProcessError as e_silent:
            logger.error("FFmpeg silent track fallback also failed", stderr=e_silent.stderr)
            return False
