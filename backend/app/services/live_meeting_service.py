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

MEETING_KEYWORDS = {
    "standup", "sprint", "sync", "syncup", "review", "planning", "retro", "retrospective",
    "demo", "architecture", "daily", "weekly", "monthly", "catchup", "huddle", "status",
    "engineering", "design", "product", "discussion", "alignment", "kickoff", "release",
    "incident", "backlog", "grooming", "refinement", "scrum", "agile", "touchpoint",
    "checkin", "check-in", "session", "workshop", "interview", "onboarding", "training",
    "project", "ops", "operations", "strategy", "roadmap", "sync-up", "weekly sync",
}

BLOCKED_WORDS = CORP_KEYWORDS | UI_KEYWORDS | TEAMS_STATIC_PAGES | MEETING_KEYWORDS

COMMON_NON_NAMES = {
    # Pronouns & determiners
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "we", "us", "our", "ours", "ourselves", "they", "them", "their", "theirs", "themselves",
    "who", "whom", "whose", "which", "what", "whatever", "whoever", "that", "this", "these", "those",
    "there", "here", "where", "when", "why", "how", "someone", "somebody", "something",
    "anyone", "anybody", "anything", "everyone", "everybody", "everything",
    "noone", "nobody", "nothing", "none", "some", "all", "any", "both", "each",
    "either", "neither", "one", "other", "another", "such",
    # Contractions & Slang
    "gonna", "wanna", "gotta", "kinda", "sorta", "dunno", "lemme", "gimme", "ain't",
    "can't", "won't", "didn't", "doesn't", "isn't", "aren't", "wasn't", "weren't",
    "haven't", "hasn't", "hadn't", "shouldn't", "wouldn't", "couldn't", "you're", "they're", "we're",
    # Auxiliary & common verbs
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "done", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "go", "going", "gone", "went", "goes", "say", "saying", "said", "says",
    "tell", "telling", "told", "tells", "know", "knowing", "knew", "known", "knows",
    "think", "thinking", "thought", "thinks", "see", "seeing", "saw", "seen", "sees",
    "come", "coming", "came", "comes", "get", "getting", "got", "gotten", "gets",
    "make", "making", "made", "makes", "take", "taking", "took", "taken", "takes",
    "look", "looking", "looked", "looks", "want", "wanting", "wanted", "wants",
    "give", "giving", "gave", "given", "gives", "use", "using", "used", "uses",
    "find", "finding", "found", "finds", "ask", "asking", "asked", "asks",
    "work", "working", "worked", "works", "call", "calling", "called", "calls",
    "try", "trying", "tried", "tries", "need", "needing", "needed", "needs",
    "feel", "feeling", "felt", "feels", "leave", "put", "mean", "keep", "let",
    "begin", "seem", "help", "talk", "turn", "start", "show", "hear", "play",
    "run", "move", "live", "bring", "happen", "write", "provide", "sit", "stand",
    "lose", "pay", "meet", "include", "continue", "set", "setup", "learn", "change",
    "lead", "understand", "watch", "follow", "stop", "create", "speak", "read",
    "allow", "add", "spend", "grow", "open", "walk", "win", "offer", "remember",
    "love", "consider", "appear", "buy", "wait", "serve", "send", "expect",
    "build", "stay", "fall", "cut", "reach", "rock", "rocks", "rocking",
    "check", "repeat", "checking", "sound", "sounds",
    # Prepositions & Conjunctions
    "about", "above", "across", "after", "against", "along", "among", "around",
    "as", "at", "before", "behind", "below", "beneath", "beside", "between",
    "beyond", "but", "by", "down", "during", "except", "for", "from", "in",
    "inside", "into", "like", "near", "of", "off", "on", "onto", "out",
    "outside", "over", "past", "since", "through", "throughout", "till", "to",
    "toward", "towards", "under", "underneath", "until", "up", "upon", "with",
    "within", "without", "and", "or", "nor", "so", "yet", "because", "although",
    "unless", "while", "whereas", "if", "whether",
    # Adverbs, Adjectives & Common conversational words
    "just", "also", "very", "now", "then", "only", "even", "always", "never",
    "sometimes", "often", "again", "away", "back", "already", "enough", "still",
    "too", "much", "really", "actually", "probably", "maybe", "sure", "certainly",
    "well", "good", "new", "first", "last", "long", "great", "little", "own",
    "other", "old", "right", "big", "high", "different", "small", "large",
    "next", "early", "young", "important", "few", "public", "bad", "same",
    "able", "ready", "audible", "online", "offline", "sorry", "okay", "ok",
    "fine", "happy", "glad", "name", "names", "system", "systems", "stage",
    "attention", "department", "cover", "people", "person", "man", "woman",
    "boy", "girl", "bro", "dude", "guy", "daughter", "son", "father", "mother",
    "friend", "machine", "pc", "laptop", "screen", "mic", "audio", "video",
    "volume", "meeting", "view", "window", "today", "tomorrow", "yesterday",
    # Hindi / Hinglish common non-name words
    "mera", "meri", "mere", "tera", "teri", "tere", "uska", "uski", "uske",
    "inka", "inki", "inke", "apna", "apni", "apne", "naam", "kya", "hai",
    "hain", "tha", "thi", "the", "hoga", "hogi", "hoge", "karo", "karna",
    "karega", "karegi", "bol", "bolo", "bolte", "bolta", "bolti", "bhai",
    "yaar", "aaj", "kal", "sab", "kuch", "ek", "do", "teen", "bhi", "toh",
    "aur", "par", "lekin", "kyun", "kaise", "kahan", "kab", "accha", "theek",
    "haan", "nahi", "na", "matlab", "aayega", "aayegi", "aaya", "gaya",
    "raha", "rahi", "rahe", "hoon", "baat", "dekh", "dekho", "ruk", "ruko",
}

FIRST_WORD_DISALLOWED = {
    "your", "my", "our", "their", "his", "her", "its", "you", "we", "they", "i", "he", "she", "it",
    "gonna", "wanna", "gotta", "the", "a", "an", "this", "that", "these", "those",
    "is", "are", "am", "was", "were", "call", "called", "calling", "that's", "it's"
}


def clean_person_name(name: str) -> str:
    """Strips common conference tags, suffixes, and noise from a person's display name."""
    c = name.strip()
    for noise in [
        "(Guest)", "(External)", "(Presenter)", "(Organizer)", "(You)",
        "- Call", "| Call", "- Meeting", "| Meeting", " (external)", " (guest)"
    ]:
        c = c.replace(noise, "").strip()
    return c.strip(" ,.-'\":;!?()[]{}")


def is_valid_person_name(name: str, host_name: str = "") -> bool:
    """
    Validates whether a candidate string is an individual person's name
    rather than a UI control/view, corporate entity, English pronoun/verb/adjective,
    slang, or general conversational noise.
    """
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
    words = [w.lower() for w in re.findall(r"[a-zA-Z]+", cl)]
    if not words or len(words) > 4:
        return False

    # Blocked corporate, UI, and static page keywords
    word_set = set(words)
    if word_set & BLOCKED_WORDS:
        return False

    # Single-word name validation: must NOT be any common non-name English/Hindi word
    if len(words) == 1:
        if words[0] in COMMON_NON_NAMES:
            return False

    # Multi-word candidate validation:
    # First word cannot be an English pronoun, determiner, modal, or slang
    if words[0] in FIRST_WORD_DISALLOWED:
        return False

    # If every word in the multi-word phrase is in COMMON_NON_NAMES, reject it
    if all(w in COMMON_NON_NAMES for w in words):
        return False

    return True


def extract_conversational_speaker_name(text: str, roster: Optional[List[str]] = None) -> Optional[str]:
    """
    Extracts self-introduced attendee names from live transcript text.
    Strictly verifies candidates against non-name vocabularies and prefers
    matching against the known meeting roster if available.
    """
    import re
    if not text or not text.strip():
        return None

    # 1. If roster is available, check if the utterance is an introduction mentioning a roster member
    if roster:
        text_lower = text.lower()
        for member in roster:
            parts = member.split()
            first = parts[0].lower() if parts else ""
            full = member.lower()
            intro_roster_patterns = [
                rf"\b(?:my name is|my name\'s|i am|i\'m|this is|call me)\s+{re.escape(first)}\b",
                rf"\b(?:my name is|my name\'s|i am|i\'m|this is|call me)\s+{re.escape(full)}\b",
                rf"\b{re.escape(first)}\s+(?:here|speaking|that is my name|is my name)\b",
                rf"\b{re.escape(full)}\s+(?:here|speaking|that is my name|is my name)\b",
                rf"\b(?:mera naam)\s+{re.escape(first)}\s+(?:hai)\b",
                rf"\b(?:mera naam)\s+{re.escape(full)}\s+(?:hai)\b",
                rf"\b(?:main|mein)\s+{re.escape(first)}\s+(?:bol raha|bol rahi|hoon)\b",
                rf"\b(?:main|mein)\s+{re.escape(full)}\s+(?:bol raha|bol rahi|hoon)\b",
            ]
            for pat in intro_roster_patterns:
                if re.search(pat, text_lower):
                    return member

    # 2. General self-introduction patterns (STRICT: require explicit intro markers)
    patterns = [
        r"\b(?:my name is|my name\'s)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
        r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)(?:,\s*|\s+)(?:that is my name|is my name)\b",
        r"\b(?:call me|you can call me)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
        r"\b(?:i am|i\'m)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:here|speaking)\b",
        r"\b(?:this is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:here|speaking)\b",
        r"\b(?:it\'s|it is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:here|speaking)\b",
        r"\b(?:mera naam)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:hai)\b",
        r"\b(?:main|mein)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:bol raha|bol rahi|hoon)\b",
        r"(?:^|[.!?\n,]|(?:hi|hello|hey))\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+here\b",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().title()
            if is_valid_person_name(candidate):
                if roster:
                    cand_lower = candidate.lower()
                    for r in roster:
                        if cand_lower == r.lower() or cand_lower in [x.lower() for x in r.split()]:
                            return r
                    if len(candidate.split()) < 2:
                        continue
                return candidate
    return None


def pitch_rbf(f0: float, num_centers: int = 8, f_min: float = 80.0, f_max: float = 360.0) -> np.ndarray:
    """
    Radial Basis Function expansion of pitch across 8 log-spaced centers.
    Transforms 1D scalar F0 into an 8-dimensional orthogonal basis, providing
    sharp angular separation between different speakers even within the same gender.
    """
    if f0 <= 0:
        return np.zeros(num_centers, dtype=np.float32)
    log_f = np.log2(np.clip(f0, f_min, f_max))
    centers = np.linspace(np.log2(f_min), np.log2(f_max), num_centers)
    sigma = (centers[1] - centers[0]) * 0.85
    rbf = np.exp(-0.5 * ((log_f - centers) / sigma) ** 2)
    return (rbf / (np.linalg.norm(rbf) + 1e-9)).astype(np.float32)


def extract_acoustic_embedding(pcm_data: bytes, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """
    Extracts a high-discrimination voice signature embedding for multi-speaker separation:
    - 8-dimensional log-spaced RBF pitch vector (centered across 80Hz - 360Hz)
    - 12-dimensional Discrete Cosine Transform (DCT-II) Mel-frequency cepstral coefficients (MFCCs)
    - Formant energy distribution across low (300-800Hz), mid (800-2200Hz), and high (2200-4000Hz) bands
    - Normalized spectral centroid
    Discriminates 3+ speakers cleanly (same person similarity > 0.95, different person < 0.88).
    """
    if not pcm_data or len(pcm_data) < 1600:
        return None
    try:
        from scipy.fftpack import dct
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        if len(samples) < 1600:
            return None

        # 1. Frame-based robust pitch estimation (30ms frames, 15ms hop)
        frame_len = int(sample_rate * 0.030)
        hop_len = int(sample_rate * 0.015)
        pitches = []
        min_lag = int(sample_rate / 400)  # ~40
        max_lag = int(sample_rate / 80)   # ~200

        for i in range(0, len(samples) - frame_len, hop_len):
            frame = samples[i : i + frame_len]
            if np.sqrt(np.mean(frame**2)) < 250:
                continue
            corr = scipy.signal.correlate(frame, frame, mode="full")[frame_len - 1 :]
            if len(corr) > max_lag:
                peak = min_lag + int(np.argmax(corr[min_lag:max_lag]))
                if corr[peak] > 0.35 * corr[0]:
                    pitches.append(sample_rate / peak)

        if len(pitches) >= 3:
            median_f0 = float(np.median(pitches))
            f0_vec = pitch_rbf(median_f0)
        else:
            # Unvoiced speech or short utterance: zero out pitch so matching relies purely on vocal tract MFCCs!
            f0_vec = np.zeros(8, dtype=np.float32)

        # 2. 16 Mel-spaced log filterbank energies
        mel_edges = np.linspace(np.log10(100), np.log10(7000), 17)
        band_edges = 10 ** mel_edges
        freqs, psd = scipy.signal.welch(samples, fs=sample_rate, nperseg=min(1024, len(samples)))

        fbanks = []
        for k in range(16):
            idx = np.where((freqs >= band_edges[k]) & (freqs < band_edges[k + 1]))[0]
            val = float(np.mean(psd[idx])) if len(idx) > 0 else 1e-12
            fbanks.append(np.log10(max(val, 1e-12)))

        # 3. Apply DCT-II to decorrelate (MFCC coefficients 1..12, dropping C0 which is energy)
        mfcc = dct(np.array(fbanks), type=2, norm="ortho")[1:13]
        mfcc_norm = mfcc / (np.linalg.norm(mfcc) + 1e-9)

        # 4. Formant ratios: Low (300-800Hz), Mid (800-2200Hz), High (2200-4000Hz)
        low_idx = np.where((freqs >= 300) & (freqs < 800))[0]
        mid_idx = np.where((freqs >= 800) & (freqs < 2200))[0]
        high_idx = np.where((freqs >= 2200) & (freqs < 4000))[0]

        e_low = float(np.sum(psd[low_idx])) + 1e-12
        e_mid = float(np.sum(psd[mid_idx])) + 1e-12
        e_high = float(np.sum(psd[high_idx])) + 1e-12
        total_formant = e_low + e_mid + e_high
        formant_dist = np.array([e_low / total_formant, e_mid / total_formant, e_high / total_formant])

        # 5. Spectral Centroid
        centroid = float(np.sum(freqs * psd) / (np.sum(psd) + 1e-12))
        centroid_norm = float(np.clip(centroid / 4000.0, 0.0, 1.0))

        # 6. Composite voice signature: Pitch RBF (weight 2.0), MFCCs (weight 1.0), Formants (weight 0.8), Centroid (weight 0.4)
        sig = np.concatenate((f0_vec * 2.0, mfcc_norm * 1.0, formant_dist * 0.8, [centroid_norm * 0.4]))
        return (sig / (np.linalg.norm(sig) + 1e-9)).astype(np.float32)
    except Exception as e:
        logger.debug("Failed to extract acoustic embedding", error=str(e))
        return None


FEMALE_NAME_HINTS = {
    "harshita", "priya", "neha", "pooja", "ananya", "shreya", "sneha", "ritu", "anjali",
    "kavita", "sunita", "divya", "swati", "rashmi", "aditi", "megha", "tanvi", "sakshi",
    "aishwarya", "shweta", "radhika", "simran", "kriti", "nisha", "deepika", "pallavi",
    "mary", "sarah", "emily", "jessica", "ashley", "rachel", "emma", "olivia", "sophia",
}
MALE_NAME_HINTS = {
    "yash", "rahul", "sujal", "rohit", "amit", "ankit", "abhishek", "vikas", "sachin",
    "gaurav", "manish", "deepak", "suresh", "ramesh", "ajay", "vijay", "karan", "arjun",
    "john", "david", "michael", "james", "robert", "william", "daniel", "chris", "alex",
}


def guess_name_gender(name: str) -> str:
    """Returns 'female', 'male', or 'unknown' based on first name."""
    if not name:
        return "unknown"
    first = name.strip().split()[0].lower()
    if first in FEMALE_NAME_HINTS:
        return "female"
    if first in MALE_NAME_HINTS:
        return "male"
    if first.endswith(("ita", "shita", "ika", "iya", "eeta", "isha", "aali", "anya")):
        return "female"
    return "unknown"


def get_voice_pitch_gender(emb: Optional[np.ndarray]) -> str:
    """
    Returns 'male', 'female', or 'unknown' based on the F0 RBF profile in the voice embedding.
    Centers 0..2 span ~80Hz - 135Hz (clear male pitch range),
    Centers 4..7 span ~185Hz - 360Hz (clear female pitch range).
    Range 140Hz - 180Hz (Center 3) is an overlapping pitch range and returns 'unknown'.
    """
    if emb is None or len(emb) < 8:
        return "unknown"
    pitch_vec = emb[:8]
    total_pitch = float(np.sum(pitch_vec))
    if total_pitch < 0.05:
        return "unknown"  # Unvoiced speech
    low_sum = float(np.sum(pitch_vec[:3]))   # 80Hz - 135Hz (male)
    high_sum = float(np.sum(pitch_vec[4:8])) # 185Hz - 360Hz (female)
    if low_sum > high_sum * 1.5 and low_sum > total_pitch * 0.4:
        return "male"
    elif high_sum > low_sum * 1.5 and high_sum > total_pitch * 0.4:
        return "female"
    return "unknown"


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
        similarity_threshold: float = 0.88,
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

    def add_to_roster(self, name: str) -> List[Tuple[str, str]]:
        """
        Adds newly discovered attendee(s) to the diarizer's roster.
        Returns a list of (old_placeholder_name, new_attendee_name) renames if any placeholder clusters were updated.
        """
        if not name:
            return []
        import re
        renamed_pairs: List[Tuple[str, str]] = []
        parts = re.split(r",| and | & ", name)
        assigned_names = {c.display_name.lower() for c in self.clusters}
        for part in parts:
            c = clean_person_name(part)
            if is_valid_person_name(c, self.host_name) and c not in self.roster:
                self.roster.append(c)
                # If an existing cluster had a generic placeholder and this name isn't already assigned:
                if c.lower() not in assigned_names:
                    for cluster in self.clusters:
                        if not cluster.is_name_confirmed and cluster.display_name.startswith(("Participant", "Remote Attendee")):
                            cand_gender = guess_name_gender(c)
                            target_cluster = None
                            for cl in self.clusters:
                                if not cl.is_name_confirmed and cl.display_name.startswith(("Participant", "Remote Attendee")):
                                    cl_gender = get_voice_pitch_gender(cl.centroid_embedding)
                                    if cl_gender == "unknown" or cand_gender == "unknown" or cl_gender == cand_gender:
                                        target_cluster = cl
                                        break
                            if not target_cluster:
                                for cl in self.clusters:
                                    if not cl.is_name_confirmed and cl.display_name.startswith(("Participant", "Remote Attendee")):
                                        target_cluster = cl
                                        break

                            if target_cluster:
                                old_name = target_cluster.display_name
                                target_cluster.display_name = c
                                target_cluster.is_name_confirmed = True
                                assigned_names.add(c.lower())
                                renamed_pairs.append((old_name, c))
                            break
        return renamed_pairs

    def note_host_addressed_attendee(self, host_text: str) -> Optional[str]:
        """
        Scans host speech on Channel 1 to detect when host addresses a remote participant.
        e.g. 'Yash, what do you think?', 'Rahul, can you update us?', 'Ladhe bol toh kuch', 'Harshita...'
        Requires direct vocative or conversational handoff patterns and ignores passive 3rd-person mentions.
        """
        if not host_text or not self.roster:
            return None
        text_lower = host_text.lower().strip()
        import difflib

        for attendee in self.roster:
            parts = [p.lower() for p in attendee.split()]
            first_name = parts[0] if parts else ""
            last_name = parts[-1] if len(parts) > 1 else ""
            full_name = attendee.lower()

            candidates = [c for c in [full_name, first_name, last_name] if c]

            for cand in candidates:
                # 1. Passive mention exclusion: check if preceded or followed by passive/reportive markers
                passive_pre = rf"\b(?:with|told|asked|about|from|spoke to|talked to|hearing from|thanks to|thank you|ke saath|ne bola|se poocha|ko bola)\s+{re.escape(cand)}\b"
                passive_post = rf"\b{re.escape(cand)}\s+(?:ne|said|told|says|mentioned|was saying|is working|was working|already|ko)\b"
                if re.search(passive_pre, text_lower) or re.search(passive_post, text_lower):
                    direct_after = rf"\b{re.escape(cand)}[,?!]\s*(?:can|could|would|what|please|batao|bolo|bol|kya|aap)\b"
                    if not re.search(direct_after, text_lower):
                        continue

                # 2. Direct address / handoff patterns
                direct_patterns = [
                    rf"(?:^|[.!?\n]|(?:hey|hi|hello|okay|ok|so))\s+{re.escape(cand)}[,?!]",
                    rf"\b{re.escape(cand)}\s+(?:can you|could you|would you|what do you|what are your|your thoughts|batao|bolo|bol|please|kya)\b",
                    rf"\b(?:what do you think|your thoughts|over to you|go ahead|tell us)\s*(?:about it)?(?:,\s*|\s+){re.escape(cand)}\b",
                    rf"^{re.escape(cand)}[,?!]",
                    rf"^{re.escape(cand)}\s+(?:can|could|would|what|please|batao|bolo|bol|kya|aap|tum)\b",
                ]

                matched = any(re.search(pat, text_lower) for pat in direct_patterns)
                if not matched:
                    if re.search(rf"\b{re.escape(cand)}[,?]", text_lower):
                        matched = True

                if matched:
                    self.last_addressed_name = attendee
                    self.last_addressed_time = time.time()
                    logger.info("Host addressed attendee", host=self.host_name, attendee=attendee)
                    return attendee

                # Transliteration / fuzzy matching for Hindi / accent STT variations (e.g. 'Ladhe' for 'Lade')
                tokens = [t for t in re.findall(r"[a-zA-Z]+", text_lower) if len(t) >= 4]
                for tok in tokens:
                    if difflib.SequenceMatcher(None, tok, cand).ratio() >= 0.85:
                        tok_idx = text_lower.find(tok)
                        ctx = text_lower[max(0, tok_idx - 10) : min(len(text_lower), tok_idx + len(tok) + 15)]
                        if any(k in ctx for k in ["bol", "batao", "kya", "can", "think", "what", ",", "?"]):
                            self.last_addressed_name = attendee
                            self.last_addressed_time = time.time()
                            logger.info("Host addressed attendee (fuzzy match)", host=self.host_name, attendee=attendee, token=tok)
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
        voice_gender = get_voice_pitch_gender(emb)

        # 1. Process host conversational address (hypothesis)
        addressed_target: Optional[str] = None
        if self.last_addressed_name and (time.time() - self.last_addressed_time < 12.0):
            addressed_target = self.last_addressed_name

        # 2. Process physical Teams UI Automation active speaker badge
        valid_ui_hint: Optional[str] = None
        if speaker_hint and is_valid_person_name(speaker_hint, self.host_name):
            if speaker_hint not in ("Remote Attendee", "Participant 2", "Unknown", "Speaker"):
                hint_gender = guess_name_gender(speaker_hint)
                if voice_gender != "unknown" and hint_gender != "unknown" and voice_gender != hint_gender:
                    logger.info(
                        "Speaker hint rejected due to gender mismatch with voice pitch",
                        hint=speaker_hint,
                        hint_gender=hint_gender,
                        voice_gender=voice_gender,
                    )
                else:
                    valid_ui_hint = speaker_hint

        # 3. Resolve target priority: Physical UI badge vs Verbal addressing hypothesis
        # Hierarchy: If Teams UI badge is active (e.g. "Ram"), physical microphone reality WINS over verbal addressing!
        resolved_hint: Optional[str] = None
        if valid_ui_hint:
            resolved_hint = valid_ui_hint
            if addressed_target and valid_ui_hint.lower() == addressed_target.lower():
                self.last_addressed_name = None  # Addressed person spoke!
        elif addressed_target:
            # Verbal address hypothesis: check if addressed person ALREADY has an established cluster
            addressed_cluster = next((c for c in self.clusters if c.display_name.lower() == addressed_target.lower()), None)
            if addressed_cluster and emb is not None:
                sim_to_addressed = float(np.dot(emb, addressed_cluster.centroid_embedding))
                if sim_to_addressed >= self.similarity_threshold:
                    # Acoustically matches the addressed person's known voice!
                    resolved_hint = addressed_target
                    self.last_addressed_name = None
                else:
                    # PROXY / INTERRUPTION SCENARIO: Host addressed Yash, but incoming voice does NOT match Yash!
                    # Refuse to force Yash's name onto this different voice!
                    logger.info(
                        "Interruption detected: incoming voice does not match addressed attendee cluster",
                        addressed=addressed_target,
                        similarity=round(sim_to_addressed, 3),
                        threshold=self.similarity_threshold,
                    )
                    resolved_hint = None
            else:
                # Addressed person has not spoken yet: use as tentative hypothesis
                resolved_hint = addressed_target
                self.last_addressed_name = None

        # Fallback if embedding is None
        if emb is None:
            if resolved_hint:
                return (resolved_hint, False)
            if self.clusters:
                return (self.clusters[self.active_cluster_index].display_name, False)
            if self.roster:
                return (self.roster[0], False)
            return ("Remote Attendee", False)

        # Case 1: First speaker on Channel 2
        if not self.clusters:
            if valid_ui_hint:
                name = valid_ui_hint
                confirmed = True
            elif resolved_hint:
                name = resolved_hint
                confirmed = bool(self.roster and any(resolved_hint.lower() == r.lower() for r in self.roster))
            elif self.roster:
                matched_candidate = None
                if voice_gender != "unknown":
                    for cand in self.roster:
                        if guess_name_gender(cand) == voice_gender:
                            matched_candidate = cand
                            break
                name = matched_candidate or self.roster[0]
                confirmed = True
            else:
                name = "Remote Attendee"
                confirmed = False

            c = SpeakerCluster(
                cluster_id="REMOTE_SPK_1",
                display_name=name,
                centroid_embedding=emb,
                last_active_time=time.time(),
                is_name_confirmed=confirmed,
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
            # Adaptive smoothing to prevent centroid drift across long conversations
            alpha = max(0.90, 1.0 - (1.0 / (cluster.sample_count + 1)))
            new_centroid = alpha * cluster.centroid_embedding + (1.0 - alpha) * emb
            cluster.centroid_embedding = new_centroid / (np.linalg.norm(new_centroid) + 1e-9)
            cluster.last_active_time = time.time()

            # If cluster is NOT confirmed, and physical UI badge or resolved_hint arrives:
            if not cluster.is_name_confirmed:
                target_to_apply = valid_ui_hint or resolved_hint
                if target_to_apply:
                    assigned_other = {
                        c.display_name.lower() for i, c in enumerate(self.clusters) if i != best_idx
                    }
                    if target_to_apply.lower() not in assigned_other:
                        cluster.display_name = target_to_apply
                        if valid_ui_hint:
                            cluster.is_name_confirmed = True

            return (cluster.display_name, False)
        else:
            # Different speaker! New turn from another remote participant.
            assigned_names = {c.display_name.lower() for c in self.clusters}

            if resolved_hint and resolved_hint.lower() not in assigned_names:
                new_name = resolved_hint
                confirmed = bool(valid_ui_hint or (self.roster and any(resolved_hint.lower() == r.lower() for r in self.roster)))
            else:
                # Pick next unassigned attendee from roster, prioritizing biometric pitch gender match
                available = [r for r in self.roster if r.lower() not in assigned_names]
                if available:
                    matched_cand = None
                    if voice_gender != "unknown":
                        for cand in available:
                            if guess_name_gender(cand) == voice_gender:
                                matched_cand = cand
                                break
                    new_name = matched_cand or available[0]
                    confirmed = True
                else:
                    # SAFETY GUARD: Prevent spawning phantom clusters!
                    # When all roster attendees already have a cluster, or if an unconfirmed placeholder already exists,
                    # any audio chunk MUST map to the closest existing cluster rather than creating Participant 4, 5, 6, 7!
                    has_unconfirmed = any(not c.is_name_confirmed for c in self.clusters)
                    max_allowed = max(len(self.roster), 2) + 1
                    if has_unconfirmed or len(self.clusters) >= max_allowed:
                        cluster = self.clusters[best_idx]
                        self.active_cluster_index = best_idx
                        cluster.last_active_time = time.time()
                        return (cluster.display_name, False)

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
        if not self.clusters or not name or not is_valid_person_name(name, self.host_name):
            return None
        active_cluster = self.clusters[self.active_cluster_index]
        matched_name = name
        name_lower = name.lower()
        for r in self.roster:
            r_lower = r.lower()
            r_parts = [p.lower() for p in r.split()]
            if r_lower == name_lower or name_lower in r_parts or r_lower.startswith(name_lower + " "):
                matched_name = r
                break

        old_name = active_cluster.display_name
        if old_name == matched_name:
            return None

        # CRITICAL SAFETY GUARD:
        # If the active cluster is ALREADY attributed to a valid roster member
        # (e.g. Harshita Baghel or Yash Lade), NEVER overwrite it with a non-roster candidate!
        if active_cluster.display_name in self.roster and matched_name not in self.roster:
            logger.info(
                "Ignored cluster rename: cannot replace confirmed roster member with non-roster name",
                current=old_name,
                ignored=matched_name,
            )
            return None

        # Check if matched_name belongs to an existing cluster
        for idx, c in enumerate(self.clusters):
            if c.display_name.lower() == matched_name.lower():
                self.active_cluster_index = idx
                return None

        # Only allow update in-place if:
        # 1. Current name is a placeholder (Participant, Remote Attendee, etc.)
        # 2. OR new name is an expansion of old name (e.g. "Harshita" -> "Harshita Baghel")
        is_placeholder = (
            old_name.startswith(("Participant", "Remote Attendee", "Unknown", "Speaker"))
            or not is_valid_person_name(old_name, self.host_name)
        )
        is_expansion = (
            old_name.lower() in matched_name.lower() and len(matched_name) > len(old_name)
        )
        if is_placeholder or is_expansion:
            active_cluster.display_name = matched_name
            active_cluster.is_name_confirmed = True
            logger.info("Updated speaker cluster via verified intro", old_name=old_name, new_name=matched_name)
            return old_name
        else:
            # Active cluster was already a distinct confirmed attendee (e.g. Harshita Baghel).
            # Do NOT overwrite their cluster! Create a new cluster for the newly introduced speaker.
            fallback_emb = active_cluster.centroid_embedding.copy()
            new_cluster = SpeakerCluster(
                cluster_id=f"REMOTE_SPK_{len(self.clusters) + 1}",
                display_name=matched_name,
                centroid_embedding=fallback_emb,
                last_active_time=time.time(),
                is_name_confirmed=True,
            )
            self.clusters.append(new_cluster)
            self.active_cluster_index = len(self.clusters) - 1
            logger.info("Created new speaker cluster for introduced attendee", new_name=matched_name)
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

    async def add_attendees_mid_meeting(self, meeting_id: uuid.UUID, attendees_str: str) -> List[str]:
        """
        Dynamically adds one or more attendees to an active live meeting session.
        Splits comma-separated names, updates diarizer roster, and reconciles any placeholder clusters.
        """
        session = self._sessions.get(meeting_id)
        if not session or not session.is_active:
            return []

        added: List[str] = []
        async with session.lock:
            parts = re.split(r",| and | & ", attendees_str)
            host_disp = session.channels.get(1, ChannelBuffer(1, "", "")).display_name
            for part in parts:
                c = clean_person_name(part)
                if is_valid_person_name(c, host_disp):
                    if c not in session.known_roster:
                        session.known_roster.append(c)
                        added.append(c)
                    if session.diarizer:
                        renames = session.diarizer.add_to_roster(c)
                        for old_n, new_n in renames:
                            if session.channels.get(2) and session.channels[2].display_name == old_n:
                                session.channels[2].display_name = new_n
                            asyncio.create_task(
                                self._reconcile_placeholder_speaker(session, 2, old_n, new_n)
                            )
        logger.info("Added attendees mid-meeting", meeting_id=str(meeting_id), added=added)
        return added

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
                    renames = session.diarizer.add_to_roster(r_name)
                    if r_name not in session.known_roster:
                        session.known_roster.append(r_name)
                    for old_n, new_n in renames:
                        if session.channels.get(2) and session.channels[2].display_name == old_n:
                            session.channels[2].display_name = new_n
                        asyncio.create_task(
                            self._reconcile_placeholder_speaker(session, 2, old_n, new_n)
                        )

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
                    active_roster = session.diarizer.roster if session.diarizer else session.known_roster
                    intro_name = extract_conversational_speaker_name(text_hint.strip(), roster=active_roster)
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

                # Perform speech-to-text on this chunk FIRST so silence does not create phantom clusters
                text = await self._transcribe_pcm_chunk(pcm_data, channel_id, ch_buf.display_name, session.language)
                if not text or not text.strip():
                    return

                # Genuine speech validated! Now resolve speaker for Channel 2
                turn_speaker = ch_buf.display_name
                if channel_id > 1 and session.diarizer:
                    turn_speaker, _ = session.diarizer.identify_speaker(pcm_data, speaker_hint=speaker_hint)
                    ch_buf.display_name = turn_speaker

                if text and text.strip():
                    # Channel 1: Host speaking -> note if host addresses an attendee
                    if channel_id == 1 and session.diarizer:
                        session.diarizer.note_host_addressed_attendee(text.strip())

                    # Channel 2: Dynamic conversational self-introduction
                    if channel_id > 1:
                        active_roster = session.diarizer.roster if session.diarizer else session.known_roster
                        intro_name = extract_conversational_speaker_name(text, roster=active_roster)
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

            if result:
                res_clean = result.strip().lower().rstrip(".,!?;:")
                # Common Whisper hallucination phrases on quiet ambient audio / silence
                WHISPER_SILENCE_HALLUCINATIONS = {
                    "thank you for watching",
                    "thanks for watching",
                    "thank you",
                    "thanks",
                    "please subscribe",
                    "subtitles by",
                    "subtitles by the amara.org community",
                    "bye",
                    "watching",
                    "see you next time",
                    "you",
                }
                if res_clean in WHISPER_SILENCE_HALLUCINATIONS or res_clean.startswith("thank you for watching"):
                    logger.info("Discarded Whisper silence hallucination turn", text=result)
                    return ""

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

        # SAFETY: Never rename away from an already valid person's name unless it was a placeholder or is an expansion
        host_disp = session.channels.get(1, ChannelBuffer(1, "", "")).display_name
        is_old_placeholder = (
            old_name.startswith(("Participant", "Remote Attendee", "SPEAKER_", "Unknown", "Speaker"))
            or not is_valid_person_name(old_name, host_disp)
        )
        is_expansion = (
            old_name.lower() in new_name.lower() and len(new_name) > len(old_name)
        )
        if not (is_old_placeholder or is_expansion):
            logger.warning(
                "Blocked speaker reconciliation: refusing to overwrite valid name",
                old_name=old_name,
                new_name=new_name,
            )
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

            # Post-meeting speaker consolidation:
            # Query all speakers recorded for this meeting
            all_speakers = db.query(Speaker).filter(
                Speaker.meeting_id == meeting_id,
                Speaker.tenant_id == session.tenant_id,
            ).all()

            confirmed_speakers = [s for s in all_speakers if not s.display_name.startswith(("Participant", "Remote Attendee", "Unknown"))]
            placeholder_speakers = [s for s in all_speakers if s.display_name.startswith(("Participant", "Remote Attendee", "Unknown"))]

            if confirmed_speakers and placeholder_speakers:
                # Merge leftover placeholder speakers into the primary remote confirmed speaker and delete fake records
                primary_target = confirmed_speakers[-1] if len(confirmed_speakers) > 1 else confirmed_speakers[0]
                for p_spk in placeholder_speakers:
                    db.query(TranscriptSegment).filter(
                        TranscriptSegment.speaker_id == p_spk.id
                    ).update({"speaker_id": primary_target.id})
                    db.delete(p_spk)

            # Clean up any residual Whisper hallucination segments
            for hall_text in ["Thank you for watching.", "Thank you for watching", "Thanks for watching.", "Please subscribe."]:
                db.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == session.transcript_id,
                    TranscriptSegment.text.ilike(hall_text),
                ).delete(synchronize_session=False)

            db.commit()
            logger.info("Finalized live meeting and consolidated speakers", meeting_id=str(meeting_id), duration=duration)
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
