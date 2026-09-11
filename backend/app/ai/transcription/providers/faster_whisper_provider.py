import os
import structlog
from app.ai.transcription.interface import TranscriptionProvider
from app.ai.transcription.schemas import (
    TranscriptionResult, 
    TranscriptionOptions, 
    TranscriptSegmentResult, 
    TranscriptWordResult
)

logger = structlog.get_logger(__name__)

class FasterWhisperProvider(TranscriptionProvider):
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError("faster-whisper is not installed. Please install it to use FasterWhisperProvider.")
            
        self.model_size = os.getenv("WHISPER_MODEL_SIZE", "large-v3")
        self.device = os.getenv("WHISPER_DEVICE", "cpu") # Use "cuda" for GPU
        self.compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8") # Use "float16" for GPU
        
        logger.info("Initializing FasterWhisperModel", model_size=self.model_size, device=self.device, compute_type=self.compute_type)
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    def transcribe(self, audio_path: str, options: TranscriptionOptions) -> TranscriptionResult:
        logger.info("Starting transcription", audio_path=audio_path)
        
        segments, info = self.model.transcribe(
            audio_path,
            language=options.language,
            beam_size=options.beam_size,
            vad_filter=options.vad_filter,
            word_timestamps=options.word_timestamps
        )
        
        canonical_segments = []
        for segment in segments:
            canonical_words = []
            if options.word_timestamps and segment.words:
                for word in segment.words:
                    canonical_words.append(
                        TranscriptWordResult(
                            start_seconds=word.start,
                            end_seconds=word.end,
                            text=word.word,
                            confidence=word.probability
                        )
                    )
            
            # Simple avg confidence if not provided directly at segment level by faster-whisper
            seg_confidence = sum([w.confidence for w in canonical_words]) / len(canonical_words) if canonical_words else 1.0
            
            canonical_segments.append(
                TranscriptSegmentResult(
                    start_seconds=segment.start,
                    end_seconds=segment.end,
                    text=segment.text,
                    confidence=seg_confidence,
                    words=canonical_words
                )
            )
            
        logger.info("Transcription completed", duration=info.duration, language=info.language)
        
        return TranscriptionResult(
            language=info.language,
            duration=info.duration,
            segments=canonical_segments,
            model_name="faster-whisper",
            model_version=self.model_size
        )
