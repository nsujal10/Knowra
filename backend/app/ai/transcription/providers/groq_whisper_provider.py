import os
import math
import tempfile
import subprocess
import httpx
import structlog
from app.core.config import settings
from app.ai.transcription.interface import TranscriptionProvider
from app.ai.transcription.schemas import (
    TranscriptionResult,
    TranscriptionOptions,
    TranscriptSegmentResult,
    TranscriptWordResult,
)

logger = structlog.get_logger(__name__)

# Groq has a 25MB file upload limit
MAX_UPLOAD_BYTES = 24 * 1024 * 1024  # 24 MB safety threshold


class GroqWhisperProvider(TranscriptionProvider):
    """
    Enterprise Cloud ASR Provider leveraging Groq's specialized LPUs for ultra-fast
    Whisper Large-V3 transcription (processing speech at 200x+ real-time speed).
    """

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "LLM_API_KEY", "")
        self.model = model or os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
        self.base_url = "https://api.groq.com/openai/v1/audio/transcriptions"

        if not self.api_key:
            raise ValueError(
                "No API key configured for GroqWhisperProvider. Please set LLM_API_KEY or GROQ_API_KEY."
            )
        logger.info("Initialized GroqWhisperProvider", model=self.model)

    def _prepare_audio(self, audio_path: str) -> tuple[str, bool]:
        """
        Ensures the audio file is within Groq's 25MB limit.
        If file exceeds 24MB or is raw WAV, compresses to high-clarity 32k mono MP3,
        allowing up to 1.5+ hours of meeting audio in a single request.
        """
        file_size = os.path.getsize(audio_path)
        ext = os.path.splitext(audio_path)[1].lower()

        # If already an MP3/M4A/AAC and under 24MB, upload directly
        if ext in [".mp3", ".m4a", ".aac", ".ogg"] and file_size <= MAX_UPLOAD_BYTES:
            return audio_path, False

        # If WAV or exceeds 24MB, compress to 32k mono MP3
        if file_size > MAX_UPLOAD_BYTES or ext in [".wav", ".pcm"]:
            temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_mp3.close()
            logger.info(
                "Compressing audio for Groq upload",
                original_bytes=file_size,
                target_path=temp_mp3.name,
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-i", audio_path,
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                "-b:a", "32k",
                temp_mp3.name,
            ]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and os.path.exists(temp_mp3.name) and os.path.getsize(temp_mp3.name) > 0:
                compressed_size = os.path.getsize(temp_mp3.name)
                logger.info("Audio compressed successfully", compressed_bytes=compressed_size)
                return temp_mp3.name, True
            else:
                logger.warning("FFmpeg compression failed, falling back to original audio", stderr=res.stderr.decode(errors="ignore"))

        return audio_path, False

    def transcribe(self, audio_path: str, options: TranscriptionOptions) -> TranscriptionResult:
        logger.info("Submitting audio to Groq Whisper Cloud", audio_path=audio_path, model=self.model)

        upload_path, is_temp = self._prepare_audio(audio_path)
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            filename = os.path.basename(upload_path)
            content_type = "audio/mpeg" if upload_path.endswith(".mp3") else "audio/wav"

            with open(upload_path, "rb") as f:
                files = {"file": (filename, f, content_type)}
                data = {
                    "model": self.model,
                    "response_format": "verbose_json",
                    "temperature": "0.0",
                    "timestamp_granularities[]": ["word", "segment"],
                }
                if options.language:
                    data["language"] = options.language

                response = httpx.post(
                    self.base_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=180.0,
                )

            if response.status_code != 200:
                logger.error(
                    "Groq Whisper API call failed",
                    status_code=response.status_code,
                    body=response.text,
                )
                raise RuntimeError(f"Groq Whisper transcription failed ({response.status_code}): {response.text}")

            res_json = response.json()
            duration = float(res_json.get("duration", 0.0))
            language = res_json.get("language", "english")

            raw_segments = res_json.get("segments", [])
            words_pool = res_json.get("words", [])

            canonical_segments: list[TranscriptSegmentResult] = []

            # Match words to segments accurately by timestamp range
            word_idx = 0
            num_words = len(words_pool)

            for seg in raw_segments:
                seg_start = float(seg.get("start", 0.0))
                seg_end = float(seg.get("end", 0.0))
                seg_text = seg.get("text", "").strip()

                avg_logprob = seg.get("avg_logprob", 0.0)
                seg_confidence = max(0.0, min(1.0, math.exp(avg_logprob))) if avg_logprob else 0.95

                seg_words: list[TranscriptWordResult] = []

                # Group words falling within this segment window
                while word_idx < num_words:
                    w = words_pool[word_idx]
                    w_start = float(w.get("start", 0.0))
                    w_end = float(w.get("end", 0.0))
                    w_text = w.get("word", "").strip()

                    # Word belongs to this segment
                    if w_start <= seg_end or w_end <= seg_end + 0.15:
                        seg_words.append(
                            TranscriptWordResult(
                                start_seconds=w_start,
                                end_seconds=w_end,
                                text=w_text,
                                confidence=seg_confidence,
                            )
                        )
                        word_idx += 1
                    else:
                        break

                canonical_segments.append(
                    TranscriptSegmentResult(
                        start_seconds=seg_start,
                        end_seconds=seg_end,
                        text=seg_text,
                        confidence=seg_confidence,
                        words=seg_words,
                    )
                )

            logger.info(
                "Groq Whisper transcription succeeded",
                duration=duration,
                segments_count=len(canonical_segments),
                words_count=len(words_pool),
            )

            return TranscriptionResult(
                language=language,
                duration=duration,
                segments=canonical_segments,
                model_name="groq-whisper",
                model_version=self.model,
            )

        finally:
            if is_temp and os.path.exists(upload_path):
                try:
                    os.remove(upload_path)
                except Exception:
                    pass
