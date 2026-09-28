import os
import math
import tempfile
import subprocess
import httpx
from typing import Optional
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

    # Context priming prompts improve verbatim accuracy by conditioning Whisper
    # Brand anchor prompt ensures correct capitalization of 'Knowra' without providing
    # vocabulary or conversational sentences that Whisper could autoregressively hallucinate during silence.
    PROMPT_EN = "Knowra."
    PROMPT_HINGLISH = "Knowra."

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "LLM_API_KEY", "")
        self.model = model or os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
        self.base_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        self._rate_limit_until: float = 0.0

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
                    "prompt": self._get_priming_prompt(options.language),
                }
                iso_lang = self._normalize_language(options.language)
                if iso_lang:
                    data["language"] = iso_lang

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

                no_speech_prob = float(seg.get("no_speech_prob", 0.0))
                if no_speech_prob > 0.40 or avg_logprob < -0.85:
                    continue

                seg_lower = seg_text.lower().strip().rstrip(".,!?;:")
                if (
                    seg_lower in ("gracias", "muchas gracias", "de nada", "merci", "danke", "thank you", "thanks for watching")
                    or "gracias" in seg_lower
                ):
                    continue

                if self._is_prompt_leak(seg_text) or self._is_foreign_hallucination(seg_text):
                    continue

                if options.language != "hi" and self._has_non_latin(seg_text):
                    cleaned_seg = self._sanitize_to_roman_hinglish(seg_text)
                    if cleaned_seg:
                        seg_text = cleaned_seg
                    elif cleaned_seg is None:
                        continue

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

    @staticmethod
    def _normalize_language(language: Optional[str]) -> Optional[str]:
        """Normalizes language strings to ISO-639-1.
        
        - English: returns 'en' to strictly decode in English.
        - Hinglish: returns 'hi' so Whisper is strictly locked to Hindi phonetics
          and NEVER misidentifies Hindi speech as Japanese, Romaji, or foreign languages.
        """
        if not language:
            return "hi"
        l = language.strip().lower()
        if l in ("en", "english", "en-in", "en-us"):
            return "en"
        return "hi"

    def _get_priming_prompt(self, language: Optional[str] = None) -> str:
        """Returns language-aware priming prompt to condition Whisper for verbatim accuracy."""
        if not language:
            return self.PROMPT_HINGLISH
        l = language.strip().lower()
        if l in ("en", "english", "en-us", "en-in"):
            return self.PROMPT_EN
        return self.PROMPT_HINGLISH

    def transcribe_bytes(self, wav_bytes: bytes, language: Optional[str] = None) -> Optional[str]:
        """Directly transcribes in-memory WAV bytes without disk I/O or ffmpeg.

        Accuracy improvements over baseline:
        - Uses whisper-large-v3 (not turbo) for higher accuracy
        - Sends a context/priming prompt to condition the model on verbatim vocabulary
        - Extended hallucination filtering catches common Whisper silence artifacts
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("live_chunk.wav", wav_bytes, "audio/wav")}

        # Build the priming prompt for verbatim output
        priming_prompt = self._get_priming_prompt(language)
        iso_lang = self._normalize_language(language)

        data = {
            "model": self.model,
            "response_format": "verbose_json",
            "temperature": "0.0",
            "prompt": priming_prompt,
        }
        if iso_lang:
            data["language"] = iso_lang

        import time
        if getattr(self, "_rate_limit_until", 0) > time.time():
            return None

        try:
            response = httpx.post(
                self.base_url,
                headers=headers,
                files=files,
                data=data,
                timeout=30.0,
            )
            if response.status_code == 200:
                return self._clean_and_validate_transcription(response.json(), language)
            elif response.status_code == 429:
                if self.model != "whisper-large-v3-turbo":
                    logger.info("Groq Whisper 429 rate limit hit. Switching dynamically to whisper-large-v3-turbo.")
                    self.model = "whisper-large-v3-turbo"
                    data["model"] = "whisper-large-v3-turbo"
                    try:
                        retry_resp = httpx.post(
                            self.base_url,
                            headers=headers,
                            files={"file": ("live_chunk.wav", wav_bytes, "audio/wav")},
                            data=data,
                            timeout=25.0,
                        )
                        if retry_resp.status_code == 200:
                            return self._clean_and_validate_transcription(retry_resp.json(), language)
                    except Exception:
                        pass
                self._rate_limit_until = time.time() + 3.0
                logger.debug("Groq Whisper rate limit active; backing off for 3s.")
                return None
            else:
                logger.warning("Groq Whisper API error in transcribe_bytes",
                               status=response.status_code, body=response.text[:200])
            return None
        except Exception as e:
            logger.debug("transcribe_bytes failed", error=str(e))
            return None

    def _clean_and_validate_transcription(self, res_data: dict, language: str) -> Optional[str]:
        """Validates Groq Whisper output, strips silence hallucinations and prompt leaks."""
        text = res_data.get("text", "").strip()
        detected_lang = (res_data.get("language") or "").lower()

        # Filter foreign languages that Whisper hallucinates on quiet noise/accents
        if detected_lang and detected_lang not in ("english", "hindi", "en", "hi", "ur", "urdu"):
            logger.debug("Filtered foreign language hallucination", detected=detected_lang, text=text)
            return None

        # Segment-level validation: check no_speech_prob and avg_logprob
        segments = res_data.get("segments", [])
        if segments:
            no_speech_probs = [float(s.get("no_speech_prob", 0.0)) for s in segments]
            avg_logprobs = [float(s.get("avg_logprob", 0.0)) for s in segments]
            max_no_speech = max(no_speech_probs) if no_speech_probs else 0.0
            avg_logprob = (sum(avg_logprobs) / len(avg_logprobs)) if avg_logprobs else 0.0

            if max_no_speech > 0.50 or avg_logprob < -1.1:
                logger.debug("Filtered complete silence artifact",
                             no_speech=max_no_speech, avg_logprob=avg_logprob, text=text)
                return None

        # Filter hallucinated silence artifacts common in Whisper (e.g. YouTube subtitles or silence noise)
        cleaned_lower = text.lower().strip()
        hallucinations = {
            "thanks for watching!", "thanks for watching.",
            "subtitles by...", "subtitles by the amara.org community",
            ".", "..", "...", "", " ",
            "the end.", "the end",
            "subscribe", "subscribe.",
            "please subscribe.", "like and subscribe.",
            "to be continued...", "to be continued",
            "продолжение следует...", "продолжение следует", "продолжение следует.",
            "aaj ka kya plan hai?", "aaj ka kya plan hai",
            "theek hai, production release friday ko karenge.",
            "theek hai, production release friday ko karenge",
            "gracias.", "gracias", "muchas gracias.", "muchas gracias",
            "de nada.", "de nada", "bueno.", "bueno", "hola.", "hola",
            "adiós.", "adios.", "adiós", "adios",
            "merci.", "merci", "merci beaucoup.", "merci beaucoup",
            "danke.", "danke", "bitte.", "bitte",
            "karen.", "karen", "tx", "tx.", "txv", "txv.", "badhein.", "badhein", "ek aawa", "ek aawa.",
            "tarek.", "tarek", "kuch bhasha", "kunchi bhasha",
            "prastut", "prastut.", "prastut prastut", "prastut prastut.",
            "प्रस्तुत", "प्रस्तुत प्रस्तुत",
            "knowra", "knowra.", "knowra sprint", "knowra, sprint",
            "data collection", "data collection.",
            "sprint planning", "database migration",
            "architecture", "architecture.",
        }
        if (
            cleaned_lower in hallucinations
            or any(h in cleaned_lower for h in ["gracias", "muchas gracias", "subtitles by", "thank you for watching"])
        ):
            logger.debug("Filtered hallucination", text=text)
            return None

        # Filter looping/stuttering hallucinations (e.g. 'ji-ji-ji-ji', 'prastut prastut', or 'data collection, data collection')
        if self._has_repetition_loop(cleaned_lower):
            logger.debug("Filtered stutter/looping hallucination", text=text)
            return None
        # Filter foreign script silence hallucinations (Russian, Japanese, Korean, CJK)
        if self._is_foreign_hallucination(text):
            logger.debug("Filtered foreign script hallucination", text=text)
            return None
        # Filter prompt leaks and meta-instructions
        if self._is_prompt_leak(text):
            logger.debug("Filtered prompt leak", text=text)
            return None
        # Also filter very short single-character outputs
        if len(cleaned_lower) <= 2 and not cleaned_lower.isalpha():
            return None

        # If language is Hinglish or English (not pure Hindi), convert any Devanagari or Urdu into clean Roman script
        if language != "hi":
            text = self._sanitize_to_roman_hinglish(text)

        return text if text and text.strip() else None

    @staticmethod
    def _has_repetition_loop(text: str) -> bool:
        """Detects autoregressive repetition loops in Whisper output (words or phrases repeated)."""
        import re
        tl = text.lower().strip().rstrip(".,!?;:")
        if not tl:
            return False
        # Stuttering with hyphens: "ji-ji-ji" or "ha-ha-ha-ha"
        if re.search(r'\b(\w{2,})(?:-\1){2,}\b', tl):
            return True
        # Single word repeated 2+ times where word length >= 4 (e.g. "prastut prastut", "aziz aziz aziz")
        if re.search(r'\b([a-zA-Z\u0900-\u097F]{4,})(?:[\s,]+)\1\b', tl):
            return True
        # Multi-word phrase or clause repeated (e.g. "data collection, data collection" or "database migration, architecture, database migration, architecture")
        if re.search(r'(.{4,40}?)(?:,\s*|\s+)\1\b', tl):
            return True
        return False

    @staticmethod
    def _is_foreign_hallucination(text: str) -> bool:
        """Detects foreign language silence hallucinations common in Whisper (Russian, Japanese, Korean, Chinese)."""
        import re
        # Cyrillic (\u0400-\u04FF), Japanese Kana (\u3040-\u30FF, \u31F0-\u31FF), CJK Ideographs (\u4E00-\u9FFF), Korean Hangul (\uAC00-\uD7AF)
        return bool(re.search(r'[\u0400-\u04FF\u3040-\u30FF\u31F0-\u31FF\u4E00-\u9FFF\uAC00-\uD7AF]', text))

    @staticmethod
    def _has_non_latin(text: str) -> bool:
        """Checks if text contains non-Latin scripts (Arabic/Urdu, Devanagari, Gurmukhi, etc.)."""
        import re
        return bool(re.search(r'[\u0600-\u06FF\u0900-\u0D7F]', text))

    @staticmethod
    def _is_prompt_leak(text: str) -> bool:
        """Detects if Whisper leaked prompt instructions, vocabulary, or conversational keywords during silence."""
        if not text:
            return False
        tl = text.lower().strip().rstrip(".,!?;:")

        # Solitary brand names or fragments without real speech
        if tl in ("knowra", "knowra.", "knowra sprint", "knowra, sprint", "knowra meeting"):
            return True

        leak_triggers = [
            "transcribe verbatim", "transcribe the following", "word-for-word",
            "in roman", "code-switch", "technical discussions", "do not translate",
            "include filler words", "speakers discuss", "without omissions",
            "technical meeting discussions", "शब्दशः", "ट्रांसक्राइब करें",
            "aaj ka kya plan hai", "production release friday",
            "production release friday ko karenge",
            "database migration me latency", "architecture check karo",
            "sprint planning aur deployment discuss", "pr review kar lena",
            "knowra technical meeting",
            "knowra, sprint", "knowra sprint",
            "sprint planning, deployment", "deployment, architecture",
            "database migration, architecture", "architecture, database migration",
            "api latency",
        ]
        if any(trig in tl for trig in leak_triggers):
            return True

        # Check for list of prompt vocabulary hallucinated on silence
        domain_tokens = ["knowra", "sprint", "deployment", "architecture", "database migration", "api latency"]
        matches = sum(1 for tok in domain_tokens if tok in tl)
        if matches >= 2 and ("," in tl or len(tl.split()) <= 8):
            return True

        return False

    def _sanitize_to_roman_hinglish(self, text: Optional[str]) -> Optional[str]:
        """Converts any Devanagari or Arabic/Urdu script text into clean Roman script Hinglish & English."""
        if not text or not text.strip():
            return None

        if self._is_prompt_leak(text):
            return None

        # If purely Latin/English alphabet already, return as is
        if not self._has_non_latin(text):
            return text.strip()

        # Call Groq fast LLM to transliterate non-Latin (Urdu/Devanagari) into Roman Hinglish
        try:
            chat_url = "https://api.groq.com/openai/v1/chat/completions"
            llm_model = getattr(settings, "LLM_MODEL", None) or os.getenv("LLM_MODEL") or "qwen/qwen3.8-27b"
            system_msg = (
                "You are an Indian meeting transcript transliterator.\n"
                "STRICT RULES:\n"
                "1. Output MUST be ONLY in English and Hinglish (written purely in the Roman / Latin alphabet).\n"
                "2. If text contains Devanagari script or Arabic/Urdu script, convert/transliterate it directly into natural Roman script Hinglish.\n"
                "3. Keep English words and technical terms in English.\n"
                "4. If the input is a prompt instruction like 'Transcribe verbatim...' or silence noise, output an empty string.\n"
                "5. NEVER output any Devanagari or Arabic/Urdu characters. Output ONLY the cleaned Romanized transcript line."
            )
            resp = httpx.post(
                chat_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": llm_model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 120,
                },
                timeout=4.0,
            )
            if resp.status_code == 200:
                cleaned = resp.json()["choices"][0]["message"]["content"].strip()
                if self._is_prompt_leak(cleaned):
                    return None
                return cleaned if cleaned else None
        except Exception as e:
            logger.debug("Hinglish transliteration fallback", error=str(e))

        return text.strip()
