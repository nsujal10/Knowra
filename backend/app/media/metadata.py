import subprocess
import json
import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

def extract_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        metadata = {
            "duration": float(data["format"].get("duration", 0)),
            "video_codec": None,
            "audio_codec": None
        }
        
        for stream in data.get("streams", []):
            if stream["codec_type"] == "video" and not metadata["video_codec"]:
                metadata["video_codec"] = stream.get("codec_name")
            elif stream["codec_type"] == "audio" and not metadata["audio_codec"]:
                metadata["audio_codec"] = stream.get("codec_name")
                
        return metadata
    except Exception as e:
        logger.error("FFprobe failed", error=str(e))
        return None
