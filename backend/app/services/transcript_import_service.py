"""
Knowra Enterprise Meeting Intelligence
Direct Transcript (.txt, .srt, .vtt) Import Service
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.storage.minio import get_storage_client

logger = structlog.get_logger(__name__)


@dataclass
class ParsedSegment:
    start_seconds: float
    end_seconds: float
    speaker_name: str
    text: str


@dataclass
class ParsedTranscriptData:
    segments: List[ParsedSegment]
    duration_seconds: float
    detected_speakers: List[str] = field(default_factory=list)


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Converts strings like '00:01:23', '01:23', '00:01:23.450', '00:01:23,450' to float seconds."""
    ts_str = ts_str.strip().replace(",", ".")
    parts = ts_str.split(":")
    try:
        if len(parts) == 3:
            h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
            return round(h * 3600 + m * 60 + s, 2)
        elif len(parts) == 2:
            m, s = float(parts[0]), float(parts[1])
            return round(m * 60 + s, 2)
        elif len(parts) == 1:
            return round(float(parts[0]), 2)
    except Exception:
        pass
    return 0.0


class TranscriptParser:
    """Robust parser for .vtt, .srt, and formatted or plain .txt transcripts."""

    @classmethod
    def parse(cls, content: str, filename: str = "") -> ParsedTranscriptData:
        clean_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
        lower_fn = filename.lower()

        if lower_fn.endswith(".vtt") or clean_content.startswith("WEBVTT"):
            return cls._parse_vtt(clean_content)
        elif lower_fn.endswith(".srt") or re.search(r"\d+\n\d{2}:\d{2}:\d{2}", clean_content):
            return cls._parse_srt(clean_content)
        else:
            return cls._parse_text(clean_content)

    @classmethod
    def _parse_vtt(cls, text: str) -> ParsedTranscriptData:
        lines = text.split("\n")
        segments: List[ParsedSegment] = []
        cue_time_pattern = re.compile(
            r"(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)"
        )

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            match = cue_time_pattern.search(line)
            if match:
                start_sec = parse_timestamp_to_seconds(match.group(1))
                end_sec = parse_timestamp_to_seconds(match.group(2))
                if end_sec <= start_sec:
                    end_sec = start_sec + 2.0

                i += 1
                cue_lines = []
                while i < len(lines) and lines[i].strip() != "" and not cue_time_pattern.search(lines[i]):
                    cue_lines.append(lines[i].strip())
                    i += 1

                cue_text = " ".join(cue_lines)
                speaker = "Speaker 1"
                # Check for <v SpeakerName> or SpeakerName:
                v_match = re.match(r"<v\s+([^>]+)>(.*)", cue_text)
                if v_match:
                    speaker = v_match.group(1).strip()
                    cue_text = re.sub(r"</v>", "", v_match.group(2)).strip()
                else:
                    spk_match = re.match(r"^([^:\n]{1,40}):\s*(.*)$", cue_text)
                    if spk_match:
                        speaker = spk_match.group(1).strip()
                        cue_text = spk_match.group(2).strip()

                if cue_text:
                    segments.append(
                        ParsedSegment(
                            start_seconds=start_sec,
                            end_seconds=end_sec,
                            speaker_name=speaker,
                            text=cue_text,
                        )
                    )
            else:
                i += 1

        if not segments:
            return cls._parse_text(text)

        speakers = sorted(list(set(s.speaker_name for s in segments)))
        total_dur = segments[-1].end_seconds if segments else 0.0
        return ParsedTranscriptData(segments=segments, duration_seconds=total_dur, detected_speakers=speakers)

    @classmethod
    def _parse_srt(cls, text: str) -> ParsedTranscriptData:
        blocks = re.split(r"\n\s*\n", text)
        segments: List[ParsedSegment] = []
        cue_time_pattern = re.compile(
            r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
        )

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            time_line_idx = -1
            match = None
            for idx, l in enumerate(lines):
                m = cue_time_pattern.search(l)
                if m:
                    time_line_idx = idx
                    match = m
                    break

            if match and time_line_idx >= 0:
                start_sec = parse_timestamp_to_seconds(match.group(1))
                end_sec = parse_timestamp_to_seconds(match.group(2))
                if end_sec <= start_sec:
                    end_sec = start_sec + 2.0

                text_lines = lines[time_line_idx + 1 :]
                cue_text = " ".join(text_lines)

                speaker = "Speaker 1"
                spk_match = re.match(r"^([^:\n]{1,40}):\s*(.*)$", cue_text)
                if spk_match:
                    speaker = spk_match.group(1).strip()
                    cue_text = spk_match.group(2).strip()

                if cue_text:
                    segments.append(
                        ParsedSegment(
                            start_seconds=start_sec,
                            end_seconds=end_sec,
                            speaker_name=speaker,
                            text=cue_text,
                        )
                    )

        if not segments:
            return cls._parse_text(text)

        speakers = sorted(list(set(s.speaker_name for s in segments)))
        total_dur = segments[-1].end_seconds if segments else 0.0
        return ParsedTranscriptData(segments=segments, duration_seconds=total_dur, detected_speakers=speakers)

    @classmethod
    def _parse_text(cls, text: str) -> ParsedTranscriptData:
        """
        Parses general text files with lines formatted as:
        - [00:15] Speaker: Hello team
        - 00:01:15 - Speaker: Hello team
        - Speaker Name: Hello team
        - Plain raw paragraphs without timestamps
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        segments: List[ParsedSegment] = []

        # Patterns for timestamped speaker dialogue
        ts_spk_pattern = re.compile(
            r"^\[?(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)\]?\s*[-–—]?\s*(?:([^:\n]{1,40}):)?\s*(.+)$"
        )
        # Pattern for "Speaker Name: text"
        spk_only_pattern = re.compile(r"^([A-Z][A-Za-z0-9\s]{1,30}):\s*(.+)$")

        current_time = 0.0
        current_speaker = "Speaker 1"

        for line in lines:
            m_ts = ts_spk_pattern.match(line)
            if m_ts and ":" in m_ts.group(1):
                raw_ts = m_ts.group(1)
                explicit_spk = m_ts.group(2)
                dialogue = m_ts.group(3).strip()

                parsed_sec = parse_timestamp_to_seconds(raw_ts)
                if parsed_sec >= current_time:
                    current_time = parsed_sec

                if explicit_spk:
                    current_speaker = explicit_spk.strip()

                # Approximate duration based on words (~150 words/min = 0.4s/word)
                word_count = max(1, len(dialogue.split()))
                est_duration = max(2.5, round(word_count * 0.38, 2))
                end_sec = round(current_time + est_duration, 2)

                segments.append(
                    ParsedSegment(
                        start_seconds=current_time,
                        end_seconds=end_sec,
                        speaker_name=current_speaker,
                        text=dialogue,
                    )
                )
                current_time = end_sec
                continue

            m_spk = spk_only_pattern.match(line)
            if m_spk:
                spk = m_spk.group(1).strip()
                dialogue = m_spk.group(2).strip()
                current_speaker = spk

                word_count = max(1, len(dialogue.split()))
                est_duration = max(2.5, round(word_count * 0.38, 2))
                end_sec = round(current_time + est_duration, 2)

                segments.append(
                    ParsedSegment(
                        start_seconds=current_time,
                        end_seconds=end_sec,
                        speaker_name=current_speaker,
                        text=dialogue,
                    )
                )
                current_time = end_sec
                continue

            # Fallback plain line/paragraph:
            # If long paragraph, split into chunks of ~35 words
            words = line.split()
            chunk_size = 35
            for k in range(0, len(words), chunk_size):
                chunk_words = words[k : k + chunk_size]
                chunk_text = " ".join(chunk_words)
                dur = max(2.5, round(len(chunk_words) * 0.38, 2))
                end_sec = round(current_time + dur, 2)

                segments.append(
                    ParsedSegment(
                        start_seconds=current_time,
                        end_seconds=end_sec,
                        speaker_name=current_speaker,
                        text=chunk_text,
                    )
                )
                current_time = end_sec

        speakers = sorted(list(set(s.speaker_name for s in segments)))
        total_dur = segments[-1].end_seconds if segments else 0.0
        return ParsedTranscriptData(segments=segments, duration_seconds=total_dur, detected_speakers=speakers)


class TranscriptImportService:
    """Coordinates end-to-end import of a transcript file into Meeting Intelligence."""

    def __init__(self, db: Session, tenant_id: UUID, user_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def import_from_text(
        self,
        filename: str,
        content: str,
        title: Optional[str] = None,
        meeting_date: Optional[datetime] = None,
        language: str = "en",
    ) -> Meeting:
        logger.info(
            "Starting transcript import",
            filename=filename,
            tenant_id=str(self.tenant_id),
            user_id=str(self.user_id),
        )

        parsed = TranscriptParser.parse(content, filename=filename)
        if not parsed.segments:
            raise ValueError("The provided file does not contain readable transcript text.")

        meeting_id = uuid.uuid4()
        media_id = uuid.uuid4()

        # Clean title
        clean_title = (title or "").strip()
        if not clean_title:
            clean_title = (
                filename.replace(".txt", "")
                .replace(".srt", "")
                .replace(".vtt", "")
                .replace("_", " ")
                .replace("-", " ")
                .strip()
                .title()
            )

        # 1. Create Meeting
        meeting = Meeting(
            id=meeting_id,
            tenant_id=self.tenant_id,
            owner_id=self.user_id,
            title=clean_title or "Imported Transcript",
            status="PROCESSING",
            meeting_date=meeting_date or datetime.now(timezone.utc),
        )
        self.db.add(meeting)
        self.db.flush()

        # 2. Upload raw transcript to Object Storage
        ext = filename.split(".")[-1] if "." in filename else "txt"
        storage_key = f"tenants/{self.tenant_id}/meetings/{meeting_id}/media/{media_id}/original/source.{ext}"
        try:
            storage = get_storage_client()
            with tempfile.NamedTemporaryFile("wb", delete=False, suffix=f".{ext}") as tmp:
                tmp.write(content.encode("utf-8"))
                tmp_path = tmp.name

            storage.upload_file("knowra-raw", storage_key, tmp_path, "text/plain")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as e:
            logger.warning("Could not persist raw transcript to MinIO", error=str(e))
            storage_key = None

        # 3. Create MediaAsset record
        media = MediaAsset(
            id=media_id,
            tenant_id=self.tenant_id,
            meeting_id=meeting.id,
            filename=filename,
            original_content_type="text/plain",
            byte_size=len(content.encode("utf-8")),
            storage_key=storage_key,
            status=MediaStatus.READY.value,
        )
        self.db.add(media)
        self.db.flush()

        # 4. Resolve or create Speakers
        speaker_map: dict[str, UUID] = {}
        for idx, spk_name in enumerate(parsed.detected_speakers):
            spk_label = f"SPEAKER_{idx + 1}"
            speaker = Speaker(
                meeting_id=meeting.id,
                tenant_id=self.tenant_id,
                speaker_label=spk_label,
                display_name=spk_name,
                user_id=self.user_id if idx == 0 else None,
            )
            self.db.add(speaker)
            self.db.flush()
            speaker_map[spk_name] = speaker.id

        # 5. Create Transcript record
        transcript = Transcript(
            tenant_id=self.tenant_id,
            meeting_id=meeting.id,
            media_asset_id=media.id,
            language=language,
            duration_seconds=round(parsed.duration_seconds, 2),
            provider_name="transcript_import",
            model_name="knowra_text_parser",
            model_version="1.0.0",
        )
        self.db.add(transcript)
        self.db.flush()

        # 6. Create TranscriptSegments & Words
        segments_for_export = []
        for seq_idx, seg in enumerate(parsed.segments):
            spk_id = speaker_map.get(seg.speaker_name)
            seg_record = TranscriptSegment(
                tenant_id=self.tenant_id,
                transcript_id=transcript.id,
                sequence_number=seq_idx,
                start_seconds=round(seg.start_seconds, 2),
                end_seconds=round(seg.end_seconds, 2),
                text=seg.text,
                confidence=0.98,
                speaker_id=spk_id,
                alignment_status="ALIGNED",
            )
            self.db.add(seg_record)
            self.db.flush()

            # Optional words breakdown for time seeking
            words_to_insert = []
            words = seg.text.split()
            w_dur = (seg.end_seconds - seg.start_seconds) / max(1, len(words))
            for w_idx, w in enumerate(words):
                w_start = round(seg.start_seconds + w_idx * w_dur, 2)
                w_end = round(w_start + w_dur, 2)
                words_to_insert.append(
                    TranscriptWord(
                        tenant_id=self.tenant_id,
                        transcript_segment_id=seg_record.id,
                        sequence_number=w_idx,
                        start_seconds=w_start,
                        end_seconds=w_end,
                        text=w,
                        confidence=0.98,
                    )
                )
            self.db.add_all(words_to_insert)

            segments_for_export.append(
                {
                    "start_seconds": seg.start_seconds,
                    "end_seconds": seg.end_seconds,
                    "text": seg.text,
                    "speaker": seg.speaker_name,
                }
            )

        self.db.commit()

        # 7. Persist Canonical Transcript JSON artifact to MinIO
        try:
            json_key = f"tenants/{self.tenant_id}/meetings/{meeting.id}/transcription/transcript.json"
            export_payload = {
                "meeting_id": str(meeting.id),
                "language": language,
                "duration": parsed.duration_seconds,
                "model_name": "knowra_text_parser",
                "model_version": "1.0.0",
                "segments": segments_for_export,
            }
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp_json:
                json.dump(export_payload, tmp_json)
                tmp_json_path = tmp_json.name

            storage = get_storage_client()
            storage.upload_file("knowra-derived", json_key, tmp_json_path, "application/json")
            if os.path.exists(tmp_json_path):
                os.remove(tmp_json_path)
        except Exception as json_err:
            logger.warning("Could not upload transcript.json artifact", error=str(json_err))

        # 8. Trigger AI Intelligence Extraction (Summaries, Actions, Decisions, Topics)
        try:
            from app.intelligence.extraction.service import MeetingIntelligenceService

            intel_service = MeetingIntelligenceService(db=self.db, tenant_id=self.tenant_id)
            intel_service.run_intelligence(meeting_id=meeting.id)
            logger.info("Generated intelligence for imported transcript", meeting_id=str(meeting.id))
        except Exception as intel_err:
            logger.warning("Could not run inline intelligence extraction", error=str(intel_err))

        # 9. Trigger Knowledge Semantic Chunking & Vector Embeddings for Search Copilot & RAG
        try:
            from app.knowledge.chunking import SemanticChunker
            from app.knowledge.embeddings.gateway import EmbeddingGateway
            from app.knowledge.models import KnowledgeChunk, KnowledgeChunkSegment

            db_segments = (
                self.db.query(TranscriptSegment)
                .filter(TranscriptSegment.transcript_id == transcript.id)
                .order_by(TranscriptSegment.sequence_number.asc())
                .all()
            )
            if db_segments:
                chunker = SemanticChunker()
                raw_chunks = chunker.chunk_segments(db_segments)

                gateway = EmbeddingGateway()
                provider = gateway.get_provider()

                for c_idx, rc in enumerate(raw_chunks):
                    emb = provider.embed_text(rc.content)
                    k_chunk = KnowledgeChunk(
                        tenant_id=self.tenant_id,
                        meeting_id=meeting.id,
                        transcript_id=transcript.id,
                        content=rc.content,
                        chunk_index=c_idx,
                        token_count=rc.token_count,
                        primary_topic=rc.primary_topic,
                        speaker_names=rc.speaker_names,
                        start_seconds=rc.start_seconds,
                        end_seconds=rc.end_seconds,
                        embedding=emb,
                    )
                    self.db.add(k_chunk)
                    self.db.flush()

                    for seg_id in rc.segment_ids:
                        self.db.add(
                            KnowledgeChunkSegment(
                                tenant_id=self.tenant_id,
                                chunk_id=k_chunk.id,
                                segment_id=seg_id,
                            )
                        )
                self.db.commit()
                logger.info(
                    "Indexed imported transcript into knowledge base",
                    chunks_count=len(raw_chunks),
                    meeting_id=str(meeting.id),
                )
        except Exception as rag_err:
            logger.warning("Knowledge chunking skipped or deferred", error=str(rag_err))

        # 10. Mark Meeting Completed
        meeting.status = "COMPLETED"
        self.db.commit()
        self.db.refresh(meeting)

        logger.info(
            "Transcript import fully completed",
            meeting_id=str(meeting.id),
            segments=len(parsed.segments),
            speakers=len(parsed.detected_speakers),
        )
        return meeting
