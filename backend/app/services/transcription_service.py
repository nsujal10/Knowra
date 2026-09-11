import json
import os
import structlog
from uuid import UUID
from sqlalchemy.orm import Session
from app.ai.transcription.schemas import TranscriptionResult
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.storage.minio import get_storage_client

logger = structlog.get_logger(__name__)

class TranscriptionService:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def save_transcription(self, meeting_id: UUID, media_id: UUID, result: TranscriptionResult):
        logger.info("Saving transcription results", meeting_id=str(meeting_id))
        
        # 1. DB Persistence
        transcript = Transcript(
            tenant_id=self.tenant_id,
            meeting_id=meeting_id,
            media_asset_id=media_id,
            language=result.language,
            duration_seconds=result.duration,
            provider_name=result.model_name or "faster_whisper",
            model_name=result.model_name,
            model_version=result.model_version
        )
        self.db.add(transcript)
        self.db.flush() # get ID
        
        for seg_idx, seg in enumerate(result.segments):
            segment_record = TranscriptSegment(
                tenant_id=self.tenant_id,
                transcript_id=transcript.id,
                sequence_number=seg_idx,
                start_seconds=seg.start_seconds,
                end_seconds=seg.end_seconds,
                text=seg.text,
                confidence=seg.confidence
            )
            self.db.add(segment_record)
            self.db.flush()
            
            words_to_insert = []
            for w_idx, word in enumerate(seg.words):
                words_to_insert.append(TranscriptWord(
                    tenant_id=self.tenant_id,
                    transcript_segment_id=segment_record.id,
                    sequence_number=w_idx,
                    start_seconds=word.start_seconds,
                    end_seconds=word.end_seconds,
                    text=word.text,
                    confidence=word.confidence
                ))
            self.db.add_all(words_to_insert)
            
        self.db.commit()

        # 2. JSON Artifact generation and Upload
        json_key = f"tenants/{self.tenant_id}/meetings/{meeting_id}/transcription/transcript.json"
        
        # create tmp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
            json.dump(result.model_dump(), tmp)
            tmp_path = tmp.name
            
        storage = get_storage_client()
        storage.upload_file("knowra-derived", json_key, tmp_path, "application/json")
        os.remove(tmp_path)
        
        logger.info("Transcription persisted successfully", transcript_id=str(transcript.id))
        return transcript
