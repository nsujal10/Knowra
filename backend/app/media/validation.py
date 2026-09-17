import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

ALLOWED_MIME_TYPES = [
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "video/x-msvideo",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/webm",
    "audio/ogg",
]

MAGIC_BYTES = {
    b'\x49\x44\x33': 'audio/mpeg',
    b'\xff\xfb': 'audio/mpeg',
    b'\xff\xf3': 'audio/mpeg',
    b'\xff\xf2': 'audio/mpeg',
    b'\x52\x49\x46\x46': 'audio/wav',
    b'\x1a\x45\xdf\xa3': 'video/webm'
}

def validate_mime_type(mime_type: str) -> bool:
    if not mime_type:
        return False
    clean_mime = mime_type.split(";")[0].strip().lower()
    return clean_mime in ALLOWED_MIME_TYPES or clean_mime.startswith("video/") or clean_mime.startswith("audio/")

def validate_file_signature(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)
            
        if not header:
            return None

        # 1. Standard MP4 / M4V / QuickTime: ISO BMFF has 'ftyp' or 'moov' at offset 4
        if len(header) >= 8 and header[4:8] in [b'ftyp', b'moov', b'wide', b'mdat']:
            return 'video/mp4'
            
        # 2. WAV file: starts with RIFF and has WAVE at bytes 8:12
        if header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WAVE':
            return 'audio/wav'
            
        # 3. WebM / MKV: Matroska/EBML container
        if header.startswith(b'\x1a\x45\xdf\xa3'):
            return 'video/webm'

        # 4. MP3 ID3 header or sync word
        if header.startswith(b'ID3') or (
            len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0 == 0xE0)
        ):
            return 'audio/mpeg'

        for signature, mime in MAGIC_BYTES.items():
            if header.startswith(signature):
                return mime
                
        # 5. Robust fallback: probe with ffprobe if header signatures were inconclusive
        from app.media.metadata import extract_metadata
        meta = extract_metadata(file_path)
        if meta and (meta.get("video_codec") or meta.get("audio_codec")):
            if meta.get("video_codec"):
                return 'video/mp4'
            return 'audio/wav'

        return None
    except Exception as e:
        logger.error("Failed to read magic bytes", error=str(e))
        return None
