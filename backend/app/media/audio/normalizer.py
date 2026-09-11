import hashlib
import os
from app.media.ffmpeg.runner import run_command

def normalize_to_canonical(input_path: str, output_path: str) -> dict:
    """
    Converts audio to canonical artifact format: 16kHz, mono, PCM s16le WAV.
    Calculates exact SHA-256 checksum dynamically during IO.
    """
    cmd = [
        "ffmpeg", "-y", 
        "-i", input_path, 
        "-vn", # strip video
        "-ac", "1", # mono
        "-ar", "16000", # 16kHz
        "-c:a", "pcm_s16le", # PCM 16-bit
        "-f", "wav", 
        output_path
    ]
    
    run_command(cmd, timeout=900)
    
    sha256 = hashlib.sha256()
    size = 0
    with open(output_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
            size += len(chunk)
            
    return {
        "checksum_sha256": sha256.hexdigest(),
        "byte_size": size,
        "sample_rate": 16000,
        "channels": 1,
        "sample_format": "s16"
    }
