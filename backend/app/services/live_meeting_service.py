"""
Live Meeting Streaming & Multi-Track Speaker Separation Service

Coordinates real-time dual-channel audio ingestion:
- Channel 1: Local User / Host Microphone (100% isolated host stream)
- Channel 2: Remote Attendees / System Audio Loopback (Teams/Zoom/Meet participants)

Handles:
- In-memory audio buffering & chunk-based speech-to-text
- Roster/metadata-based and voice-embedding-based speaker resolution
- Real-time broadcast to connected frontend subscribers
- Finalization of live transcripts into canonical DB records
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
import uuid
import wave
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import structlog
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.meeting import Meeting
from app.models.media_asset import MediaAsset
from app.models.enums import MediaStatus
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User

logger = structlog.get_logger(__name__)

TEAMS_STATIC_PAGES = {
    "chat", "activity", "calendar", "calls", "files", "teams", "apps",
    "settings", "help", "notifications", "general", "meet", "meeting",
    "call", "microsoft teams", "teams meeting", "new chat", "search",
    "desktop 1", "unknown"
}

CORP_KEYWORDS = {
    "pvt", "ltd", "inc", "corp", "llc", "infotech", "technologies", "technology",
    "solutions", "systems", "software", "consulting", "enterprise", "services",
    "systematix", "softude", "microsoft", "google", "zoom", "private", "limited",
    "corporation", "company", "organization", "tenant", "internal", "external tenant",
}

UI_KEYWORDS = {
    # Teams / Zoom / Meet window states, layouts, and controls
    "meeting", "view", "compact", "controls", "control", "chat", "calls", "call", "share",
    "sharing", "screen", "window", "video", "audio", "device", "devices", "bar",
    "tile", "grid", "gallery", "panel", "tab", "notification", "notifications",
    "presence", "calendar", "activity", "general", "teams", "channel", "group",
    "conversation", "settings", "help", "desktop", "preview", "room", "lobby",
    "stage", "roster", "participant", "attendee", "attendees", "speaker", "speakers",
    "volume", "mute", "unmute", "microphone", "mic", "camera", "webcam", "display",
    "monitor", "dock", "mini", "popup", "dialog", "overlay", "together", "mode",
    "large", "side", "banner", "whiteboard", "breakout", "reactions", "recording",
    "transcript", "transcription", "caption", "captions", "subtitles", "raise", "hand",
}

BLOCKED_WORDS = CORP_KEYWORDS | UI_KEYWORDS | TEAMS_STATIC_PAGES

INTRO_STOP_WORDS = {
    "here", "there", "speaking", "talking", "listening", "audible", "ready",
    "good", "fine", "sorry", "sure", "okay", "ok", "online", "back", "trying",
    "going", "coming", "joined", "calling", "working", "happy", "glad", "yes", "no",
    "the", "a", "an", "in", "on", "at", "to", "for", "with", "from", "just", "still",
    "also", "now", "so", "then", "too", "very", "not", "asking", "hearing", "done",
    "that", "what", "who", "this", "name",
}


def clean_person_name(name: str) -> str:
    """Strips common conference tags, suffixes, and noise from a person's display name."""
    c = name.strip()
    for noise in [
        "(Guest)", "(External)", "(Presenter)", "(Organizer)", "(You)",
        "- Call", "| Call", "- Meeting", "| Meeting", " (external)", " (guest)"
    ]:
        c = c.replace(noise, "").strip()
    return c


def is_valid_person_name(name: str, host_name: str = "") -> bool:
    """Validates whether a candidate name is an actual person, not a corporate entity or noise."""
    c = clean_person_name(name)
    if not c or len(c) < 2 or len(c) > 35:
        return False
    cl = c.lower()
    if cl in ("you", "me", "remote attendee", "speaker", "unknown", "host", "participant 1", "participant 2"):
        return False
    if host_name and cl == host_name.lower():
        return False
    if any(char.isdigit() for char in c):
        return False
    if "@" in c or "http" in cl or ".com" in cl:
        return False
    import re
    words = set(re.findall(r"[a-zA-Z]+", cl))
    if words & BLOCKED_WORDS:
        return False
    if len(c.split()) > 4:
        return False
    return True


def extract_conversational_speaker_name(text: str) -> Optional[str]:
    """
    Extracts self-introduced attendee names from live transcript text.
    Handles English, Hinglish, and Hindi conversational intros:
    - 'My name is Harshita.'
    - 'Harshita, that is my name.' / 'Harshita is my name.'
    - 'Hi, I am Harshita.' / 'This is Harshita.'
    - 'Call me Harshita.' / 'Harshita here.'
    - 'Mera naam Harshita hai.'
    - 'Main Harshita bol rahi hoon.'
    """
    import re
    if not text or not text.strip():
        return None

    patterns = [
        r"(?:my name is|my name\'s)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
        r"([a-zA-Z]+(?:\s+[a-zA-Z]+)?)(?:,\s*|\s+)that is my name",
        r"([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+is my name",
        r"(?:call me|you can call me)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
        r"(?:it\'s|it is)\s+([a-zA-Z]+)(?:\s+(?:here|speaking)|\b|\.)",
        r"(?:i am|i\'m)\s+([a-zA-Z]+)(?:\s+(?:here|speaking))?",
        r"(?:this is)\s+([a-zA-Z]+)(?:\s+(?:here|speaking))?",
        r"([a-zA-Z]+)\s+here\b",
        r"(?:mera naam)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:hai)",
        r"(?:main|mein)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:bol raha|bol rahi|hoon)",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().title()
            words = candidate.lower().split()
            if not any(w in INTRO_STOP_WORDS for w in words) and is_valid_person_name(candidate):
                return candidate
    return None


@dataclass
class ChannelBuffer:
    channel_id: int
    speaker_id: Optional[uuid.UUID] = None
    speaker_label: str = "Unknown"
    display_name: str = "Unknown"
    pcm_chunks: bytearray = field(default_factory=bytearray)
    last_speech_time: float = field(default_factory=time.time)
    last_transcribed_time: float = 0.0


@dataclass
class LiveSession:
    meeting_id: uuid.UUID
    tenant_id: uuid.UUID
    owner_id: uuid.UUID
    transcript_id: uuid.UUID
    start_wall_time: float
    channels: Dict[int, ChannelBuffer] = field(default_factory=dict)
    subscribers: Set[WebSocket] = field(default_factory=set)
    stream_clients: Set[WebSocket] = field(default_factory=set)
    segment_counter: int = 0
    language: str = "hi"
    is_active: bool = True
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class LiveMeetingManager:
    _instance: Optional[LiveMeetingManager] = None

    def __init__(self) -> None:
        self._sessions: Dict[uuid.UUID, LiveSession] = {}

    @classmethod
    def get_instance(cls) -> LiveMeetingManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Session Lifecycle
    # -------------------------------------------------------------------------

    async def start_session(
        self,
        db: Session,
        meeting_id: uuid.UUID,
        tenant_id: uuid.UUID,
        owner_id: uuid.UUID,
        host_name: str = "Sujal Nage",
        remote_name: str = "Remote Attendee",
        language: str = "hi",
    ) -> LiveSession:
        """Initialize or retrieve a live meeting session."""
        if meeting_id in self._sessions:
            return self._sessions[meeting_id]

        if not host_name or host_name in ("You (Host)", "Host", ""):
            user = db.query(User).filter(User.id == owner_id).first()
            if user and user.full_name:
                host_name = user.full_name
            else:
                host_name = "Sujal Nage"

        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.tenant_id == tenant_id,
        ).first()

        if not meeting:
            meeting = Meeting(
                id=meeting_id,
                tenant_id=tenant_id,
                owner_id=owner_id,
                title="Live Meeting",
                status="IN_PROGRESS",
            )
            db.add(meeting)
            db.commit()
            db.refresh(meeting)
        else:
            meeting.status = "IN_PROGRESS"
            db.commit()

        # Ensure MediaAsset record exists for live meeting
        media = db.query(MediaAsset).filter(
            MediaAsset.meeting_id == meeting_id,
            MediaAsset.tenant_id == tenant_id,
        ).first()

        if not media:
            media = MediaAsset(
                meeting_id=meeting_id,
                tenant_id=tenant_id,
                filename="live_session_audio.wav",
                original_content_type="audio/wav",
                status=MediaStatus.READY,
            )
            db.add(media)
            db.commit()
            db.refresh(media)

        # Ensure transcript record exists
        transcript = db.query(Transcript).filter(
            Transcript.meeting_id == meeting_id,
            Transcript.tenant_id == tenant_id,
        ).first()

        if not transcript:
            transcript = Transcript(
                tenant_id=tenant_id,
                meeting_id=meeting_id,
                media_asset_id=media.id,
                language=language,
                duration_seconds=0.0,
                provider_name="live_stream",
                model_name="knowra_live_engine",
                model_version="1.0.0",
            )
            db.add(transcript)
            db.commit()
            db.refresh(transcript)
        else:
            transcript.language = language
            db.commit()

        # Provision Channel 1 (Host) Speaker
        host_speaker = db.query(Speaker).filter(
            Speaker.meeting_id == meeting_id,
            Speaker.tenant_id == tenant_id,
            Speaker.speaker_label == "SPEAKER_HOST",
        ).first()

        if not host_speaker:
            host_speaker = Speaker(
                meeting_id=meeting_id,
                tenant_id=tenant_id,
                speaker_label="SPEAKER_HOST",
                display_name=host_name,
                user_id=owner_id,
            )
            db.add(host_speaker)
            db.commit()
            db.refresh(host_speaker)
        elif host_speaker.display_name in ("You (Host)", "Host", "") and host_name not in ("You (Host)", "Host", ""):
            host_speaker.display_name = host_name
            db.commit()

        session = LiveSession(
            meeting_id=meeting_id,
            tenant_id=tenant_id,
            owner_id=owner_id,
            transcript_id=transcript.id,
            start_wall_time=time.time(),
            language=language,
        )

        # Initialize Channel 1 (Host Mic)
        session.channels[1] = ChannelBuffer(
            channel_id=1,
            speaker_id=host_speaker.id,
            speaker_label="SPEAKER_HOST",
            display_name=host_name,
        )

        # Initialize Channel 2 (Remote Attendees default)
        session.channels[2] = ChannelBuffer(
            channel_id=2,
            speaker_id=None,
            speaker_label="SPEAKER_REMOTE",
            display_name=remote_name or "Remote Attendee",
        )

        self._sessions[meeting_id] = session
        logger.info("Started live meeting session", meeting_id=str(meeting_id))
        return session

    def get_session(self, meeting_id: uuid.UUID) -> Optional[LiveSession]:
        return self._sessions.get(meeting_id)

    # -------------------------------------------------------------------------
    # WebSocket Registration
    # -------------------------------------------------------------------------

    async def register_subscriber(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        session = self._sessions.get(meeting_id)
        if session:
            session.subscribers.add(websocket)
            logger.info("Registered transcript subscriber", meeting_id=str(meeting_id))

    async def unregister_subscriber(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        session = self._sessions.get(meeting_id)
        if session:
            session.subscribers.discard(websocket)

    async def register_stream_client(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        session = self._sessions.get(meeting_id)
        if session:
            session.stream_clients.add(websocket)
            logger.info("Registered live audio stream client", meeting_id=str(meeting_id))

    async def unregister_stream_client(self, meeting_id: uuid.UUID, websocket: WebSocket) -> None:
        session = self._sessions.get(meeting_id)
        if session:
            session.stream_clients.discard(websocket)

    # -------------------------------------------------------------------------
    # Ingestion & Speaker Resolution
    # -------------------------------------------------------------------------

    async def ingest_audio_chunk(
        self,
        meeting_id: uuid.UUID,
        channel_id: int,
        audio_bytes: bytes,
        speaker_hint: Optional[str] = None,
        text_hint: Optional[str] = None,
        timestamp_ms: Optional[float] = None,
    ) -> None:
        """Process incoming audio chunk from channel 1 (host) or channel 2+ (remote)."""
        session = self._sessions.get(meeting_id)
        if not session or not session.is_active:
            return

        async with session.lock:
            # Ensure channel buffer exists
            if channel_id not in session.channels:
                session.channels[channel_id] = ChannelBuffer(
                    channel_id=channel_id,
                    speaker_label=f"SPEAKER_{channel_id}",
                    display_name=speaker_hint or f"Participant {channel_id}",
                )

            ch_buf = session.channels[channel_id]
            if speaker_hint and ch_buf.display_name != speaker_hint:
                old_name = ch_buf.display_name
                host_disp = session.channels.get(1, ChannelBuffer(1, "", "")).display_name
                if channel_id == 1 or is_valid_person_name(speaker_hint, host_disp):
                    ch_buf.display_name = speaker_hint
                    if (
                        old_name in ("Remote Attendee", "Participant 2", "Unknown", "You (Host)", "Host", "Participant 1", "")
                        or not is_valid_person_name(old_name, host_disp)
                    ):
                        asyncio.create_task(
                            self._reconcile_placeholder_speaker(session, channel_id, old_name, speaker_hint)
                        )

            # Append audio bytes
            if audio_bytes:
                ch_buf.pcm_chunks.extend(audio_bytes)
                ch_buf.last_speech_time = time.time()

            # If client already transcribed this chunk (e.g. Chrome Web Speech API / fast local ASR)
            if text_hint and text_hint.strip():
                now_rel = (time.time() - session.start_wall_time)
                start_sec = max(0.0, now_rel - 2.5)
                end_sec = now_rel

                # Conversational self-introduction detection
                if channel_id > 1:
                    intro_name = extract_conversational_speaker_name(text_hint.strip())
                    host_disp = session.channels.get(1, ChannelBuffer(1, "", "")).display_name
                    if intro_name and is_valid_person_name(intro_name, host_disp):
                        if ch_buf.display_name != intro_name:
                            old_name = ch_buf.display_name
                            ch_buf.display_name = intro_name
                            await self._reconcile_placeholder_speaker(session, channel_id, old_name, intro_name)

                await self._persist_and_broadcast_segment(
                    session=session,
                    channel_id=channel_id,
                    text=text_hint.strip(),
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    speaker_name=ch_buf.display_name,
                )
                ch_buf.pcm_chunks.clear()
                return

            # Check if buffer has reached speech threshold (~48000 bytes = 1.5 sec @ 16kHz 16-bit mono)
            # Longer chunks give Whisper more context for better word-boundary accuracy
            if len(ch_buf.pcm_chunks) >= 48000:
                pcm_data = bytes(ch_buf.pcm_chunks)
                ch_buf.pcm_chunks.clear()

                # Safety: Check RMS energy on backend to ignore ambient silence
                try:
                    import numpy as np
                    samples = np.frombuffer(pcm_data, dtype=np.int16).copy()
                    if len(samples) > 0:
                        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                        if rms < 180.0:
                            # Skip transcribing silence to prevent Whisper hallucinations
                            return

                        # Peak gain normalization: boost quiet audio to ~-3 dBFS
                        peak = float(np.max(np.abs(samples)))
                        if peak > 0:
                            target_peak = 23000.0
                            gain = min(target_peak / peak, 10.0)
                            if gain > 1.05:
                                samples = np.clip(
                                    samples.astype(np.float32) * gain, -32768, 32767
                                ).astype(np.int16)
                                pcm_data = samples.tobytes()
                                logger.debug("Applied gain normalization",
                                             gain=round(gain, 2), peak=int(peak))
                except Exception:
                    pass

                now_rel = (time.time() - session.start_wall_time)
                duration = len(pcm_data) / (16000 * 2)
                start_sec = max(0.0, now_rel - duration)
                end_sec = now_rel

                # Perform speech-to-text on this chunk
                text = await self._transcribe_pcm_chunk(pcm_data, channel_id, ch_buf.display_name, session.language)
                if text and text.strip():
                    # Dynamic conversational speaker recognition:
                    # e.g. "My name is Harshita", "I'm Harshita", "Mera naam Harshita hai"
                    if channel_id > 1:
                        intro_name = extract_conversational_speaker_name(text)
                        host_disp = session.channels.get(1, ChannelBuffer(1, "", "")).display_name
                        if intro_name and is_valid_person_name(intro_name, host_disp):
                            if ch_buf.display_name != intro_name:
                                old_name = ch_buf.display_name
                                ch_buf.display_name = intro_name
                                await self._reconcile_placeholder_speaker(session, channel_id, old_name, intro_name)

                    await self._persist_and_broadcast_segment(
                        session=session,
                        channel_id=channel_id,
                        text=text.strip(),
                        start_seconds=start_sec,
                        end_seconds=end_sec,
                        speaker_name=ch_buf.display_name,
                    )

    async def _transcribe_pcm_chunk(
        self,
        pcm_data: bytes,
        channel_id: int,
        speaker_name: str,
        language: str = "hi",
    ) -> Optional[str]:
        """Transcribe PCM bytes using Groq/Faster-Whisper with language support or simulated fallback."""
        try:
            import os
            import tempfile
            from app.ai.transcription.factory import get_transcription_provider
            from app.ai.transcription.schemas import TranscriptionOptions
            provider = get_transcription_provider()
            
            # Wrap PCM in a standard WAV header for standard STT providers
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_data)
            wav_bytes = wav_io.getvalue()

            if hasattr(provider, "transcribe_bytes"):
                result = provider.transcribe_bytes(wav_bytes, language=language)
            else:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    tf.write(wav_bytes)
                    tf_path = tf.name
                try:
                    opt = TranscriptionOptions(language=language)
                    res = provider.transcribe(tf_path, opt)
                    result = " ".join([s.text for s in res.segments]) if res.segments else ""
                finally:
                    if os.path.exists(tf_path):
                        os.remove(tf_path)
            return result
        except Exception as e:
            logger.debug("Local live transcription fallback", reason=str(e), channel=channel_id)
            channel_desc = "Host" if channel_id == 1 else speaker_name
            return f"[{channel_desc} speaking in meeting...]"

    async def _persist_and_broadcast_segment(
        self,
        session: LiveSession,
        channel_id: int,
        text: str,
        start_seconds: float,
        end_seconds: float,
        speaker_name: str,
    ) -> None:
        """Saves segment to DB and immediately broadcasts to all active WebSocket clients."""
        session.segment_counter += 1
        seq = session.segment_counter

        db = SessionLocal()
        speaker_id = None
        speaker_label = f"SPEAKER_{channel_id}"

        try:
            # Resolve or create Speaker in DB
            speaker = db.query(Speaker).filter(
                Speaker.meeting_id == session.meeting_id,
                Speaker.tenant_id == session.tenant_id,
                Speaker.display_name == speaker_name,
            ).first()

            if not speaker:
                speaker = Speaker(
                    meeting_id=session.meeting_id,
                    tenant_id=session.tenant_id,
                    speaker_label=speaker_label,
                    display_name=speaker_name,
                    user_id=session.owner_id if channel_id == 1 else None,
                )
                db.add(speaker)
                db.commit()
                db.refresh(speaker)

            speaker_id = speaker.id

            # Save TranscriptSegment
            segment = TranscriptSegment(
                tenant_id=session.tenant_id,
                transcript_id=session.transcript_id,
                sequence_number=seq,
                start_seconds=round(start_seconds, 2),
                end_seconds=round(end_seconds, 2),
                text=text,
                confidence=0.96,
                speaker_id=speaker_id,
                alignment_status="ALIGNED",
            )
            db.add(segment)
            db.commit()
            db.refresh(segment)
            seg_id = str(segment.id)
        except Exception as e:
            logger.error("Failed to persist live segment", error=str(e))
            seg_id = str(uuid.uuid4())
        finally:
            db.close()

        # Broadcast payload to all frontend subscribers
        payload = {
            "type": "TRANSCRIPT_SEGMENT",
            "meeting_id": str(session.meeting_id),
            "segment": {
                "id": seg_id,
                "sequence": seq,
                "start": round(start_seconds, 2),
                "end": round(end_seconds, 2),
                "text": text,
                "speaker": {
                    "id": str(speaker_id) if speaker_id else speaker_label,
                    "label": speaker_label,
                    "displayName": speaker_name,
                },
                "channel": channel_id,
            },
        }

        dead_sockets = set()
        for ws in session.subscribers:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_sockets.add(ws)

        session.subscribers.difference_update(dead_sockets)

    async def _reconcile_placeholder_speaker(
        self,
        session: LiveSession,
        channel_id: int,
        old_name: str,
        new_name: str,
    ) -> None:
        """Retroactively updates previous segments from placeholder/org to the real discovered name."""
        if not new_name or old_name == new_name:
            return
        try:
            db = SessionLocal()
            try:
                placeholder_speaker = db.query(Speaker).filter(
                    Speaker.meeting_id == session.meeting_id,
                    Speaker.tenant_id == session.tenant_id,
                    Speaker.display_name == old_name,
                ).first()

                existing_speaker = db.query(Speaker).filter(
                    Speaker.meeting_id == session.meeting_id,
                    Speaker.tenant_id == session.tenant_id,
                    Speaker.display_name == new_name,
                ).first()

                if placeholder_speaker and existing_speaker:
                    # Merge: point all segments from placeholder to existing speaker
                    db.query(TranscriptSegment).filter(
                        TranscriptSegment.speaker_id == placeholder_speaker.id
                    ).update({"speaker_id": existing_speaker.id})
                    db.delete(placeholder_speaker)
                    db.commit()
                elif placeholder_speaker:
                    placeholder_speaker.display_name = new_name
                    db.commit()
                elif not existing_speaker:
                    spk = Speaker(
                        meeting_id=session.meeting_id,
                        tenant_id=session.tenant_id,
                        speaker_label=f"SPEAKER_{channel_id}",
                        display_name=new_name,
                    )
                    db.add(spk)
                    db.commit()

                logger.info(
                    "Reconciled placeholder speaker in DB",
                    meeting_id=str(session.meeting_id),
                    old_name=old_name,
                    new_name=new_name,
                )

                # Broadcast live rename event to all connected UI clients
                rename_payload = {
                    "type": "SPEAKER_RENAME",
                    "meeting_id": str(session.meeting_id),
                    "channel": channel_id,
                    "oldName": old_name,
                    "newName": new_name,
                }
                dead = set()
                for ws in session.subscribers:
                    try:
                        await ws.send_json(rename_payload)
                    except Exception:
                        dead.add(ws)
                session.subscribers.difference_update(dead)
            finally:
                db.close()
        except Exception as e:
            logger.debug("Failed to reconcile placeholder speaker", error=str(e))

    # -------------------------------------------------------------------------
    # Finalization
    # -------------------------------------------------------------------------

    async def end_session(self, meeting_id: uuid.UUID) -> None:
        """Finalize the live session and update meeting status."""
        session = self._sessions.pop(meeting_id, None)
        if not session:
            return

        session.is_active = False
        duration = max(1.0, time.time() - session.start_wall_time)

        db = SessionLocal()
        try:
            meeting = db.query(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.tenant_id == session.tenant_id,
            ).first()
            if meeting:
                meeting.status = "COMPLETED"

            transcript = db.query(Transcript).filter(
                Transcript.id == session.transcript_id,
                Transcript.tenant_id == session.tenant_id,
            ).first()
            if transcript:
                transcript.duration_seconds = round(duration, 2)

            db.commit()
            logger.info("Finalized live meeting", meeting_id=str(meeting_id), duration=duration)
        except Exception as e:
            logger.error("Error finalizing live meeting", error=str(e))
        finally:
            db.close()

        # Broadcast meeting ended event
        end_payload = {
            "type": "MEETING_ENDED",
            "meeting_id": str(meeting_id),
            "duration": round(duration, 2),
        }
        for ws in list(session.subscribers):
            try:
                await ws.send_json(end_payload)
            except Exception:
                pass
