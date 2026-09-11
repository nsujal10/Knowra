import json
import os
import tempfile
import structlog
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, selectinload

from app.ai.diarization.alignment.engine import TemporalAlignmentEngine
from app.ai.diarization.schemas import DiarizationResult
from app.models.diarization_run import DiarizationRun
from app.models.speaker import Speaker
from app.models.speaker_segment import SpeakerSegment
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.storage.minio import get_storage_client

logger = structlog.get_logger(__name__)


class DiarizationService:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def save_diarization(
        self,
        meeting_id: UUID,
        media_id: UUID,
        result: DiarizationResult,
        job_id: Optional[UUID] = None,
    ) -> DiarizationRun:
        log = logger.bind(meeting_id=str(meeting_id), media_id=str(media_id))
        log.info("Persisting diarization results")

        # 1. Create or update DiarizationRun
        run = (
            self.db.query(DiarizationRun)
            .filter(
                DiarizationRun.media_asset_id == media_id,
                DiarizationRun.tenant_id == self.tenant_id,
            )
            .first()
        )

        if not run:
            run = DiarizationRun(
                tenant_id=self.tenant_id,
                media_asset_id=media_id,
                job_id=job_id,
                provider_name=result.model_name,
                model_name=result.model_version,
            )
            self.db.add(run)
            self.db.flush()

        run.status = "COMPLETED"
        run.speakers_count = len(result.speakers)
        run.completed_at = datetime.now(timezone.utc)

        # 2. Synchronize meeting-scoped Speaker records
        existing_speakers = (
            self.db.query(Speaker)
            .filter(
                Speaker.meeting_id == meeting_id,
                Speaker.tenant_id == self.tenant_id,
            )
            .all()
        )
        speaker_by_label: Dict[str, Speaker] = {
            s.speaker_label: s for s in existing_speakers
        }

        # Ensure all detected speakers exist in DB
        all_labels = set(result.speakers) | {s.speaker_label for s in result.segments}
        for label in sorted(all_labels):
            if label not in speaker_by_label:
                # Generate user-friendly display name (e.g. SPEAKER_00 -> Speaker 1)
                try:
                    num = int(label.split("_")[-1]) + 1
                    display_name = f"Speaker {num}"
                except (ValueError, IndexError):
                    display_name = label.replace("_", " ").title()

                new_speaker = Speaker(
                    tenant_id=self.tenant_id,
                    meeting_id=meeting_id,
                    speaker_label=label,
                    display_name=display_name,
                )
                self.db.add(new_speaker)
                self.db.flush()
                speaker_by_label[label] = new_speaker

        # 3. Insert SpeakerSegment records (Decoupled parallel timeline)
        # Delete existing segments for this run to avoid duplicates on retry
        self.db.query(SpeakerSegment).filter(
            SpeakerSegment.diarization_run_id == run.id,
            SpeakerSegment.tenant_id == self.tenant_id,
        ).delete()

        speaker_segments_to_add = [
            SpeakerSegment(
                tenant_id=self.tenant_id,
                diarization_run_id=run.id,
                speaker_id=speaker_by_label[seg.speaker_label].id,
                start_seconds=seg.start_seconds,
                end_seconds=seg.end_seconds,
                confidence=seg.confidence,
            )
            for seg in result.segments
            if seg.speaker_label in speaker_by_label
        ]
        self.db.add_all(speaker_segments_to_add)

        # 4. Temporal Alignment Engine: Attribute ASR segments
        transcript = (
            self.db.query(Transcript)
            .options(selectinload(Transcript.segments))
            .filter(
                Transcript.meeting_id == meeting_id,
                Transcript.tenant_id == self.tenant_id,
            )
            .first()
        )

        if transcript and transcript.segments:
            engine = TemporalAlignmentEngine()
            for t_seg in transcript.segments:
                alignment = engine.align_segment(
                    t_seg.start_seconds,
                    t_seg.end_seconds,
                    result.segments,
                )
                if alignment.speaker_label and alignment.speaker_label in speaker_by_label:
                    t_seg.speaker_id = speaker_by_label[alignment.speaker_label].id
                else:
                    t_seg.speaker_id = None

                t_seg.alignment_confidence = alignment.alignment_confidence
                t_seg.alignment_status = alignment.alignment_status

        self.db.commit()

        # 5. Store immutable raw diarization JSON artifact in MinIO
        json_key = f"tenants/{self.tenant_id}/meetings/{meeting_id}/diarization/diarization.json"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
            json.dump(result.model_dump(), tmp)
            tmp_path = tmp.name

        try:
            storage = get_storage_client()
            storage.upload_file(
                "knowra-derived",
                json_key,
                tmp_path,
                "application/json",
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        log.info(
            "Diarization successfully saved and aligned",
            speakers_count=len(speaker_by_label),
            segments_count=len(speaker_segments_to_add),
        )
        return run

    def get_speakers_for_meeting(self, meeting_id: UUID) -> List[Speaker]:
        return (
            self.db.query(Speaker)
            .filter(
                Speaker.meeting_id == meeting_id,
                Speaker.tenant_id == self.tenant_id,
            )
            .order_by(Speaker.speaker_label)
            .all()
        )

    def update_speaker(
        self,
        speaker_id: UUID,
        display_name: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> Optional[Speaker]:
        speaker = (
            self.db.query(Speaker)
            .filter(
                Speaker.id == speaker_id,
                Speaker.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not speaker:
            return None

        if display_name is not None:
            speaker.display_name = display_name
        if user_id is not None:
            speaker.user_id = user_id

        self.db.commit()
        self.db.refresh(speaker)
        return speaker
