import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

ALLOWED_MIME_TYPES = ["video/mp4", "audio/mpeg", "audio/wav", "video/webm"]

MAGIC_BYTES = {
    b'\x00\x00\x00\x18ftyp': 'video/mp4',
    b'\x00\x00\x00\x20ftyp': 'video/mp4',
    b'\x49\x44\x33': 'audio/mpeg',
    b'\xff\xfb': 'audio/mpeg',
    b'\xff\xf3': 'audio/mpeg',
    b'\xff\xf2': 'audio/mpeg',
    b'\x52\x49\x46\x46': 'audio/wav',
    b'\x1a\x45\xdf\xa3': 'video/webm'
}

def validate_mime_type(mime_type: str) -> bool:
    return mime_type in ALLOWED_MIME_TYPES

def validate_file_signature(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            
        for signature, mime in MAGIC_BYTES.items():
            if header.startswith(signature):
                return mime
                
        # WAV requires extra RIFF checks
        if header.startswith(b'RIFF') and header[8:12] == b'WAVE':
            return 'audio/wav'
            
        return None
    except Exception as e:
        logger.error("Failed to read magic bytes", error=str(e))
        return None
