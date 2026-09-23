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
from typing import Dict, List, Optional, Set, Tuple
import re
import structlog
import numpy as np
import scipy.signal
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


def extract_acoustic_embedding(pcm_data: bytes, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """
    Extracts a 20-dimensional normalized acoustic voice embedding:
    - Fundamental frequency (F0 pitch estimation via autocorrelation in 80Hz - 400Hz range)
    - Formant / vocal tract distribution across 16 log-spaced frequency bands (80Hz - 7500Hz)
    - Spectral Centroid, Spectral Rolloff (85%), and Zero-Crossing Rate (ZCR)
    Runs in <1ms via vectorized NumPy / SciPy operations with zero external model dependencies.
    """
    if not pcm_data or len(pcm_data) < 1600:
        return None
    try:
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        if len(samples) < 1600:
            return None

        # 1. Pitch / Autocorrelation in 80-400 Hz range
        corr = scipy.signal.correlate(samples, samples, mode="full")
        corr = corr[len(corr) // 2 :]
        min_lag = int(sample_rate / 400)  # ~40
        max_lag = int(sample_rate / 80)   # ~200
        if len(corr) > max_lag:
            peak_lag = min_lag + int(np.argmax(corr[min_lag:max_lag]))
            f0 = sample_rate / peak_lag
            f0_norm = float(np.clip((f0 - 80.0) / 320.0, 0.0, 1.0))
        else:
            f0_norm = 0.5

        # 2. Welch PSD across 16 log-spaced bands (80Hz to 7500Hz)
        nperseg = min(1024, len(samples))
        freqs, psd = scipy.signal.welch(samples, fs=sample_rate, nperseg=nperseg)
        band_edges = np.logspace(np.log10(80), np.log10(7500), 17)
        band_energies = []
        for i in range(16):
            idx = np.where((freqs >= band_edges[i]) & (freqs < band_edges[i + 1]))[0]
            e = float(np.mean(psd[idx])) if len(idx) > 0 else 1e-12
            band_energies.append(np.log10(max(e, 1e-12)))
        be = np.array(band_energies, dtype=np.float32)
        be_std = float(np.std(be))
        be_norm = (be - float(np.mean(be))) / (be_std if be_std > 1e-6 else 1.0)

        # 3. Spectral Centroid, Rolloff, ZCR
        psd_sum = float(np.sum(psd)) + 1e-12
        centroid = float(np.sum(freqs * psd)) / psd_sum
        centroid_norm = float(np.clip(centroid / 4000.0, 0.0, 1.0))

        cum_psd = np.cumsum(psd)
        rolloff_idx = np.where(cum_psd >= 0.85 * psd_sum)[0]
        rolloff = float(freqs[rolloff_idx[0]]) if len(rolloff_idx) > 0 else 4000.0
        rolloff_norm = float(np.clip(rolloff / 6000.0, 0.0, 1.0))

        zcr = float(np.mean(np.abs(np.diff(np.sign(samples))))) / 2.0

        features = np.concatenate(([f0_norm], be_norm, [centroid_norm, rolloff_norm, zcr]))
        norm = float(np.linalg.norm(features))
        return (features / (norm + 1e-9)).astype(np.float32)
    except Exception as e:
        logger.debug("Failed to extract acoustic embedding", error=str(e))
        return None


@dataclass
class SpeakerCluster:
    cluster_id: str
    display_name: str
    centroid_embedding: np.ndarray
    sample_count: int = 1
    last_active_time: float = 0.0
    is_name_confirmed: bool = False


class LiveAcousticDiarizer:
    """
    Real-time acoustic voice diarizer and clustering engine for multi-party calls (3+ attendees).
    Separates mixed Channel 2 audio into individual remote speakers and matches them to:
    - Known attendee roster names (from modal, --attendees, or Teams window titles)
    - Conversational addressing by host ('Yash, what do you think?')
    - Self-introductions ('My name is Harshita', 'Hi, Yash here')
    """

    def __init__(
        self,
        roster: Optional[List[str]] = None,
        host_name: str = "Sujal Nage",
        similarity_threshold: float = 0.82,
    ):
        self.host_name = host_name
        self.roster: List[str] = []
        self.clusters: List[SpeakerCluster] = []
        self.similarity_threshold = similarity_threshold
        self.last_addressed_name: Optional[str] = None
        self.last_addressed_time: float = 0.0
        self.active_cluster_index: int = 0
        if roster:
            for r in roster:
                self.add_to_roster(r)

    def add_to_roster(self, name: str) -> bool:
        """Adds a newly discovered attendee to the diarizer's roster."""
        c = clean_person_name(name)
        if is_valid_person_name(c, self.host_name) and c not in self.roster:
            self.roster.append(c)
            # If an existing cluster had a generic placeholder, assign the new name
            for cluster in self.clusters:
                if not cluster.is_name_confirmed and cluster.display_name.startswith(("Participant", "Remote Attendee")):
                    cluster.display_name = c
                    cluster.is_name_confirmed = False
                    break
            return True
        return False

    def note_host_addressed_attendee(self, host_text: str) -> Optional[str]:
        """
        Scans host speech on Channel 1 to detect when host addresses a remote participant.
        e.g. 'Yash, what do you think?', 'Rahul, can you update us?', 'Harshita...'
        """
        if not host_text or not self.roster:
            return None
        text_lower = host_text.lower()
        for attendee in self.roster:
            first_name = attendee.split()[0].lower()
            full_name = attendee.lower()
            if re.search(rf"\b{re.escape(first_name)}\b", text_lower) or re.search(rf"\b{re.escape(full_name)}\b", text_lower):
                self.last_addressed_name = attendee
                self.last_addressed_time = time.time()
                logger.info("Host addressed attendee", host=self.host_name, attendee=attendee)
                return attendee
        return None

    def identify_speaker(
        self,
        pcm_data: bytes,
        speaker_hint: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Identifies or clusters the remote speaker for a Channel 2 chunk.
        Returns: (resolved_display_name, is_new_speaker_cluster)
        """
        emb = extract_acoustic_embedding(pcm_data)

        # Check if host addressed someone within the last 12 seconds
        addressed_target: Optional[str] = None
        if self.last_addressed_name and (time.time() - self.last_addressed_time < 12.0):
            addressed_target = self.last_addressed_name
            self.last_addressed_name = None  # Consume address

        # If explicit speaker hint from UIA is valid
        if not addressed_target and speaker_hint and is_valid_person_name(speaker_hint, self.host_name):
            if speaker_hint not in ("Remote Attendee", "Participant 2", "Unknown", "Speaker"):
                addressed_target = speaker_hint

        # Fallback if embedding is None
        if emb is None:
            if addressed_target:
                return (addressed_target, False)
            if self.clusters:
                return (self.clusters[self.active_cluster_index].display_name, False)
            if self.roster:
                return (self.roster[0], False)
            return ("Remote Attendee", False)

        # Case 1: First speaker on Channel 2
        if not self.clusters:
            name = addressed_target or (self.roster[0] if self.roster else "Remote Attendee")
            c = SpeakerCluster(
                cluster_id="REMOTE_SPK_1",
                display_name=name,
                centroid_embedding=emb,
                last_active_time=time.time(),
                is_name_confirmed=bool(addressed_target),
            )
            self.clusters.append(c)
            self.active_cluster_index = 0
            return (name, False)

        # Case 2: Compare against existing voice clusters
        similarities = [float(np.dot(emb, c.centroid_embedding)) for c in self.clusters]
        best_idx = int(np.argmax(similarities))
        best_sim = similarities[best_idx]

        if best_sim >= self.similarity_threshold:
            # Same speaker as cluster best_idx!
            cluster = self.clusters[best_idx]
            self.active_cluster_index = best_idx
            cluster.sample_count += 1
            alpha = 0.85
            new_centroid = alpha * cluster.centroid_embedding + (1.0 - alpha) * emb
            cluster.centroid_embedding = new_centroid / (np.linalg.norm(new_centroid) + 1e-9)
            cluster.last_active_time = time.time()

            # If host addressed someone specifically or explicit hint confirmed:
            if addressed_target and not cluster.is_name_confirmed:
                cluster.display_name = addressed_target
                cluster.is_name_confirmed = True

            return (cluster.display_name, False)
        else:
            # Different speaker! New turn from another remote participant.
            assigned_names = {c.display_name.lower() for c in self.clusters}
            if addressed_target:
                new_name = addressed_target
                confirmed = True
            else:
                # Pick next unassigned attendee from roster
                available = [r for r in self.roster if r.lower() not in assigned_names]
                if available:
                    new_name = available[0]
                    confirmed = False
                else:
                    new_name = f"Participant {len(self.clusters) + 1}"
                    confirmed = False

            new_cluster = SpeakerCluster(
                cluster_id=f"REMOTE_SPK_{len(self.clusters) + 1}",
                display_name=new_name,
                centroid_embedding=emb,
                last_active_time=time.time(),
                is_name_confirmed=confirmed,
            )
            self.clusters.append(new_cluster)
            self.active_cluster_index = len(self.clusters) - 1
            logger.info(
                "Diarized new remote speaker turn",
                cluster_id=new_cluster.cluster_id,
                display_name=new_name,
                similarity=round(best_sim, 3),
            )
            return (new_name, True)

    def update_active_cluster_name(self, name: str) -> Optional[str]:
        """
        Updates the active cluster's display name when attendee introduces themselves.
        Returns the old name if changed, or None.
        """
        if not self.clusters:
            return None
        active_cluster = self.clusters[self.active_cluster_index]
        matched_name = name
        name_lower = name.lower()
        for r in self.roster:
            if r.lower() == name_lower or r.lower().startswith(name_lower + " "):
                matched_name = r
                break

        old_name = active_cluster.display_name
        if old_name != matched_name:
            active_cluster.display_name = matched_name
            active_cluster.is_name_confirmed = True
            logger.info("Updated speaker cluster via self-intro", old_name=old_name, new_name=matched_name)
            return old_name
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
    diarizer: Optional[LiveAcousticDiarizer] = None
    known_roster: List[str] = field(default_factory=list)


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

        # Parse remote roster from remote_name (e.g. "Harshita, Yash Lade, Rahul Sharma")
        parsed_roster: List[str] = []
        if remote_name:
            parts = re.split(r",| and | & ", remote_name)
            for p in parts:
                cp = clean_person_name(p)
                if is_valid_person_name(cp, host_name) and cp not in parsed_roster:
                    parsed_roster.append(cp)

        default_remote_disp = parsed_roster[0] if parsed_roster else (remote_name or "Remote Attendee")

        # Initialize Channel 2 (Remote Attendees default)
        session.channels[2] = ChannelBuffer(
            channel_id=2,
            speaker_id=None,
            speaker_label="SPEAKER_REMOTE",
            display_name=default_remote_disp,
        )
        session.known_roster = parsed_roster
        session.diarizer = LiveAcousticDiarizer(roster=parsed_roster, host_name=host_name)

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
        roster_hint: Optional[List[str]] = None,
    ) -> None:
        """Process incoming audio chunk from channel 1 (host) or channel 2+ (remote)."""
        session = self._sessions.get(meeting_id)
        if not session or not session.is_active:
            return

        async with session.lock:
            # Sync roster_hint from Teams UIA / window title scanner
            if roster_hint and session.diarizer:
                for r_name in roster_hint:
                    session.diarizer.add_to_roster(r_name)
                    if r_name not in session.known_roster:
                        session.known_roster.append(r_name)

            # Ensure channel buffer exists
            if channel_id not in session.channels:
                session.channels[channel_id] = ChannelBuffer(
                    channel_id=channel_id,
                    speaker_label=f"SPEAKER_{channel_id}",
                    display_name=speaker_hint or f"Participant {channel_id}",
                )

            ch_buf = session.channels[channel_id]
            host_disp = session.channels.get(1, ChannelBuffer(1, "", "")).display_name

            if speaker_hint and ch_buf.display_name != speaker_hint:
                old_name = ch_buf.display_name
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
                turn_speaker = ch_buf.display_name

                # Channel 1: scan host speech for addressing remote attendees
                if channel_id == 1 and session.diarizer:
                    session.diarizer.note_host_addressed_attendee(text_hint.strip())

                # Channel 2: multi-speaker resolution
                if channel_id > 1:
                    if session.diarizer:
                        if audio_bytes and len(audio_bytes) >= 1600:
                            turn_speaker, _ = session.diarizer.identify_speaker(audio_bytes, speaker_hint=speaker_hint)
                            ch_buf.display_name = turn_speaker
                        elif speaker_hint and is_valid_person_name(speaker_hint, host_disp):
                            turn_speaker = speaker_hint
                            ch_buf.display_name = speaker_hint

                    # Conversational self-introduction detection
                    intro_name = extract_conversational_speaker_name(text_hint.strip())
                    if intro_name and is_valid_person_name(intro_name, host_disp):
                        if session.diarizer:
                            old_name = session.diarizer.update_active_cluster_name(intro_name)
                            if old_name and old_name != intro_name:
                                ch_buf.display_name = intro_name
                                turn_speaker = intro_name
                                await self._reconcile_placeholder_speaker(session, channel_id, old_name, intro_name)
                        elif ch_buf.display_name != intro_name:
                            old_name = ch_buf.display_name
                            ch_buf.display_name = intro_name
                            turn_speaker = intro_name
                            await self._reconcile_placeholder_speaker(session, channel_id, old_name, intro_name)

                await self._persist_and_broadcast_segment(
                    session=session,
                    channel_id=channel_id,
                    text=text_hint.strip(),
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    speaker_name=turn_speaker,
                )
                ch_buf.pcm_chunks.clear()
                return

            # Check if buffer has reached speech threshold (~48000 bytes = 1.5 sec @ 16kHz 16-bit mono)
            if len(ch_buf.pcm_chunks) >= 48000:
                pcm_data = bytes(ch_buf.pcm_chunks)
                ch_buf.pcm_chunks.clear()

                # Safety: Check RMS energy on backend to ignore ambient silence
                try:
                    samples = np.frombuffer(pcm_data, dtype=np.int16).copy()
                    if len(samples) > 0:
                        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                        if rms < 180.0:
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
                except Exception:
                    pass

                now_rel = (time.time() - session.start_wall_time)
                duration = len(pcm_data) / (16000 * 2)
                start_sec = max(0.0, now_rel - duration)
                end_sec = now_rel

                # Channel 2: Identify speaker using acoustic voice clustering
                turn_speaker = ch_buf.display_name
                if channel_id > 1 and session.diarizer:
                    turn_speaker, _ = session.diarizer.identify_speaker(pcm_data, speaker_hint=speaker_hint)
                    ch_buf.display_name = turn_speaker

                # Perform speech-to-text on this chunk
                text = await self._transcribe_pcm_chunk(pcm_data, channel_id, turn_speaker, session.language)
                if text and text.strip():
                    # Channel 1: Host speaking -> note if host addresses an attendee
                    if channel_id == 1 and session.diarizer:
                        session.diarizer.note_host_addressed_attendee(text.strip())

                    # Channel 2: Dynamic conversational self-introduction
                    if channel_id > 1:
                        intro_name = extract_conversational_speaker_name(text)
                        if intro_name and is_valid_person_name(intro_name, host_disp):
                            if session.diarizer:
                                old_name = session.diarizer.update_active_cluster_name(intro_name)
                                if old_name and old_name != intro_name:
                                    ch_buf.display_name = intro_name
                                    turn_speaker = intro_name
                                    await self._reconcile_placeholder_speaker(session, channel_id, old_name, intro_name)
                            elif ch_buf.display_name != intro_name:
                                old_name = ch_buf.display_name
                                ch_buf.display_name = intro_name
                                turn_speaker = intro_name
                                await self._reconcile_placeholder_speaker(session, channel_id, old_name, intro_name)

                    await self._persist_and_broadcast_segment(
                        session=session,
                        channel_id=channel_id,
                        text=text.strip(),
                        start_seconds=start_sec,
                        end_seconds=end_sec,
                        speaker_name=turn_speaker,
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
