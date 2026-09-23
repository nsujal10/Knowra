"""
Knowra Desktop Meeting Companion (Method 3 Implementation)

Captures dual-channel audio directly from desktop applications (Teams.exe, Zoom.exe, Meet):
  Channel 1: Local Host Microphone (100% isolated host speech)
  Channel 2: Remote Attendees (via Windows WASAPI Loopback / System Audio)

Features:
- Dual-channel real-time audio streaming to Knowra live meeting WebSocket
- Full Hindi (हिंदी), Hinglish, and English multi-speaker detection & simulation
- Windows WASAPI loopback device discovery for Teams.exe capture
- Interactive diagnostics and audio device enumeration

Usage:
  # 1. Hindi simulation sync (Host + Rahul Tech Lead + Priya PM discussing sprint & decisions)
  python scripts/desktop_meeting_companion.py --meeting-id <UUID> --hindi

  # 2. English simulation sync
  python scripts/desktop_meeting_companion.py --meeting-id <UUID> --simulate

  # 3. Live hardware capture (Host Mic Channel 1 + Teams Loopback Channel 2)
  python scripts/desktop_meeting_companion.py --meeting-id <UUID>

  # 4. List all audio devices on Windows
  python scripts/desktop_meeting_companion.py --list-devices
"""

import argparse
import asyncio
import base64
import http.server
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from typing import Callable, List, Optional, Set

# Ensure UTF-8 output on Windows console for Hindi characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import websockets
except ImportError:
    print("[Error] websockets library not found. Run: pip install websockets")
    sys.exit(1)

import math
import numpy as np
import scipy.signal


def detect_host_display_name() -> str:
    """
    Auto-detects the host's real name instead of generic 'You (Host)'.
    Checks:
    1. Environment variable: KNOWRA_HOST_NAME
    2. Git config user.name (e.g. 'Sujal Nage')
    3. Formatted Windows OS login (e.g. 'sujal.nage' -> 'Sujal Nage')
    4. Fallback: 'Sujal Nage'
    """
    env_name = os.getenv("KNOWRA_HOST_NAME")
    if env_name and env_name.strip():
        return env_name.strip()
    try:
        git_res = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if git_res.returncode == 0 and git_res.stdout.strip():
            return git_res.stdout.strip()
    except Exception:
        pass
    try:
        login = os.getlogin()
        if login:
            parts = [p.capitalize() for p in login.replace(".", " ").replace("_", " ").split()]
            if parts:
                return " ".join(parts)
    except Exception:
        pass
    return "Sujal Nage"


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


def is_valid_person_name(name: str, host_name: str = "Sujal Nage") -> bool:
    """
    Validates whether a candidate string is an individual person's name
    rather than a UI control/view (e.g. 'Meeting compact view'),
    company/tenant name (e.g. 'Systematix Infotech Pvt Ltd'),
    group chat channel (e.g. 'Gets 2026'), email, English pronoun/verb/adjective,
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
    # Must not contain digits (e.g. 'Gets 2026')
    if any(char.isdigit() for char in c):
        return False
    # Must not contain @ or urls
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


class TeamsLiveAttendeeTracker:
    """
    Monitors Microsoft Teams (and other meeting apps) in real time:
    1. Inspects Windows UI Automation (uiautomation) for active speaker badges
       ('... is speaking', '... is talking', unmuted active video tiles).
    2. Scans Teams window titles to extract meeting participants ('Meeting with Alex, Sarah').
    3. Maintains a live attendee roster, logging new participants as they join.
    4. Provides dynamic speaker attribution on Channel 2 so speech is assigned to the real person.
    """

    def __init__(self, initial_attendees: Optional[List[str]] = None, host_name: str = ""):
        self.host_name = host_name
        self.known_roster: List[str] = []
        if initial_attendees:
            for a in initial_attendees:
                import re
                for sub in re.split(r",| and | & ", a):
                    cleaned = clean_person_name(sub)
                    if (
                        cleaned
                        and is_valid_person_name(cleaned, host_name=self.host_name)
                        and cleaned not in self.known_roster
                        and cleaned != self.host_name
                        and cleaned.lower() != "you"
                    ):
                        self.known_roster.append(cleaned)

        self.current_speaker: str = self.known_roster[0] if self.known_roster else "Remote Attendee"
        self.last_detected_speaker: Optional[str] = None
        self.last_detection_time: float = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._has_uia = False

        try:
            import uiautomation
            self._has_uia = True
        except ImportError:
            pass

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._tracker_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def add_attendee(self, name: str) -> bool:
        """Adds a newly discovered attendee to the call roster."""
        cleaned = clean_person_name(name)
        if (
            is_valid_person_name(cleaned, host_name=self.host_name)
            and cleaned not in self.known_roster
        ):
            with self._lock:
                self.known_roster.append(cleaned)
                if self.current_speaker in ("Remote Attendee", "Unknown", ""):
                    self.current_speaker = cleaned
            timestamp_str = time.strftime("%H:%M:%S")
            print(f"[{timestamp_str}] 👤 [Teams Roster] Detected attendee in call: {cleaned}")
            return True
        return False

    def set_active_speaker(self, name: str):
        """Sets the currently active speaker with a timestamp."""
        cleaned = clean_person_name(name)
        if is_valid_person_name(cleaned, host_name=self.host_name):
            self.add_attendee(cleaned)
            with self._lock:
                old_speaker = self.last_detected_speaker
                self.last_detected_speaker = cleaned
                self.last_detection_time = time.time()
                self.current_speaker = cleaned
            if old_speaker != cleaned:
                timestamp_str = time.strftime("%H:%M:%S")
                print(f"[{timestamp_str}] 🎙️ [Teams Active Speaker] Identified: {cleaned}")

    def get_known_roster(self) -> List[str]:
        """Returns a copy of all known attendees in the call roster."""
        with self._lock:
            return list(self.known_roster)

    def get_active_speaker_hint(self) -> Optional[str]:
        """
        Returns active speaker detected via Teams UI Automation within the last 7.0 seconds.
        Returns None when no badge is active so acoustic voice clustering resolves the speaker.
        """
        with self._lock:
            if self.last_detected_speaker and (time.time() - self.last_detection_time < 7.0):
                return self.last_detected_speaker
            return None

    def get_current_speaker(self) -> str:
        """Returns the most up-to-date speaker name for Channel 2 audio chunks."""
        with self._lock:
            # If an active speaker was detected within the last 7 seconds, attribute to them
            if self.last_detected_speaker and (time.time() - self.last_detection_time < 7.0):
                return self.last_detected_speaker
            if self.current_speaker and self.current_speaker not in ("Remote Attendee", "Unknown", ""):
                return self.current_speaker
            if self.known_roster:
                return self.known_roster[0]
            return "Remote Attendee"

    def _tracker_loop(self):
        """Background thread polling Windows UI Automation and window titles."""
        while self._running:
            try:
                self._scan_window_titles()
                if self._has_uia:
                    self._scan_teams_uia()
            except Exception:
                pass
            time.sleep(0.4)

    def _scan_window_titles(self):
        """Scans window titles using Win32 API to find Teams meeting titles and attendees."""
        try:
            import ctypes
            from ctypes import wintypes
            import re
            user32 = ctypes.windll.user32

            # Ensure this thread is attached to the interactive 'Default' desktop
            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
            except Exception:
                pass

            found_titles: List[str] = []

            def enum_cb(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        found_titles.append(buff.value)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

            for t in found_titles:
                t_clean = t.strip()
                t_lower = t_clean.lower()
                if "microsoft teams" in t_lower or "teams" in t_lower:
                    # In Teams, title is pipe or dash separated:
                    # e.g. "Chat with Harshita, Yash Lade | Systematix Infotech Pvt Ltd | ... | Microsoft Teams"
                    # or "Harshita, Yash Lade, Rahul | Systematix Infotech Pvt Ltd | ... | Microsoft Teams"
                    # or "Meeting with Harshita, Rahul | Microsoft Teams"
                    pipe_parts = [p.strip() for p in t_clean.split("|")]
                    for part in pipe_parts:
                        pl = part.lower()
                        if any(k in pl for k in ["meeting with", "call with", "chat with"]):
                            for kw in ["meeting with", "call with", "chat with"]:
                                if kw in pl:
                                    after = part[pl.find(kw) + len(kw):].strip()
                                    for n in re.split(r",| and | & ", after):
                                        sub_clean = clean_person_name(n)
                                        if is_valid_person_name(sub_clean, host_name=self.host_name):
                                            self.add_attendee(sub_clean)
                        elif not any(static_tab in pl for static_tab in TEAMS_STATIC_PAGES):
                            for sub in re.split(r",| and | & ", part):
                                clean_sub = clean_person_name(sub)
                                if is_valid_person_name(clean_sub, host_name=self.host_name):
                                    self.add_attendee(clean_sub)
        except Exception:
            pass

    def _scan_teams_uia(self):
        """Inspects Microsoft Teams UI elements for 'is speaking' badges and active video tiles."""
        try:
            import uiautomation as auto
            teams_win = auto.WindowControl(searchDepth=2, SubName="Microsoft Teams")
            if not teams_win.Exists(0.05):
                teams_win = auto.WindowControl(searchDepth=2, SubName="Teams")
            if not teams_win.Exists(0.05):
                teams_win = auto.WindowControl(searchDepth=2, ClassName="TeamsWebView")

            if teams_win.Exists(0.05):
                for ctrl in teams_win.GetChildren():
                    name = ctrl.Name or ""
                    nl = name.lower()
                    if "is speaking" in nl or "is talking" in nl:
                        candidate = name.split(" is speaking")[0].split(" is talking")[0].strip()
                        clean_cand = clean_person_name(candidate)
                        if clean_cand and is_valid_person_name(clean_cand, self.host_name):
                            # Resolve against roster if possible
                            matched = clean_cand
                            with self._lock:
                                for r in self.known_roster:
                                    if clean_cand.lower() == r.lower() or clean_cand.lower() in [p.lower() for p in r.split()]:
                                        matched = r
                                        break
                            self.set_active_speaker(matched)
                            return
        except Exception:
            pass


HINDI_CONVERSATION = [
    (1, "You (Host)", "नमस्ते टीम, आज की मीटिंग में हम नए आर्किटेक्चर और स्प्रिंट टारगेट्स पर बात करेंगे।"),
    (2, "Rahul (Tech Lead)", "हाँ, मैंने डेटाबेस माइग्रेशन और इंडेक्स ऑप्टिमाइज़ेशन का काम पूरा कर लिया है। अब क्वेरी लैटेंसी 70% कम हो गई है।"),
    (2, "Priya (Product Manager)", "बहुत बढ़िया राहुल। क्या हम शुक्रवार तक नया सर्च और लाइव ट्रांसक्रिप्ट फीचर प्रोडक्शन में डिप्लॉय कर सकते हैं?"),
    (1, "You (Host)", "ज़रूर, गुरुवार को फाइनल एंड-टू-एंड टेस्टिंग होगी और शुक्रवार दोपहर 2 बजे डिप्लॉय करेंगे।"),
    (2, "Rahul (Tech Lead)", "मैं गुरुवार शाम तक टेस्टिंग रिपोर्ट, बैकअप प्लान और डिप्लॉयमेंट चेकलिस्ट तैयार रखूँगा।"),
    (2, "Priya (Product Manager)", "मैं क्लाइंट्स और स्टेकहोल्डर्स को न्यू रिलीज़ के नोट्स और यूज़र डॉक्युमेंटेशन भेज दूंगी।"),
    (1, "You (Host)", "परफेक्ट, सभी एक्शन आइटम्स और टाइमलाइन्स कन्फर्म हो गए हैं। मीटिंग यहीं समाप्त करते हैं।"),
]

ENGLISH_CONVERSATION = [
    (1, "You (Host)", "Welcome everyone to our weekly architecture and sprint sync."),
    (2, "Alex (Product)", "Thanks! I reviewed the PR for the live meeting capture, looks rock solid."),
    (2, "Sarah (Lead Eng)", "I have a quick question about the Web Audio dual-stream routing and latency."),
    (1, "You (Host)", "Sure Sarah, go ahead. The host mic is isolated on channel 1, remote audio on channel 2."),
    (2, "Sarah (Lead Eng)", "Great, so that completely avoids cross-talk issues with 3 or more attendees."),
    (2, "Alex (Product)", "Exactly what our enterprise clients were asking for! We'll deploy on Friday."),
    (1, "You (Host)", "Awesome, let's wrap up and inspect the generated transcript, decisions, and action items."),
]


async def run_simulation(ws_url: str, meeting_id: str, language: str = "en", host_name: str = "Sujal Nage"):
    """Simulates dual-track audio streaming with realistic speaker turns in Hindi or English."""
    is_hindi = language.lower() in ["hi", "hindi", "hinglish"]
    conversation = HINDI_CONVERSATION if is_hindi else ENGLISH_CONVERSATION
    lang_label = "Hindi (हिंदी)" if is_hindi else "English"

    print(f"\n========================================================")
    print(f" Knowra Desktop Companion - Live Multi-Speaker Simulation")
    print(f" Language   : {lang_label}")
    print(f" Host Name  : {host_name} (Channel 1 - Local Mic)")
    print(f" Meeting ID : {meeting_id}")
    print(f" Server WS  : {ws_url}")
    print(f" Channels   : Ch 1 (Host Mic) | Ch 2 (Teams Attendees)")
    print(f"========================================================\n")

    try:
        async with websockets.connect(ws_url) as ws:
            print(f"[Knowra Companion] Successfully connected to live stream!")
            print(f"[Knowra Companion] Streaming live dialogue turns...\n")

            # 1 second of 16kHz 16-bit mono PCM silence
            dummy_pcm = b"\x00" * 32000
            dummy_b64 = base64.b64encode(dummy_pcm).decode("utf-8")

            for idx, (channel, speaker, speech_text) in enumerate(conversation, start=1):
                actual_speaker = host_name if (channel == 1 and speaker == "You (Host)") else speaker
                timestamp_str = time.strftime("%H:%M:%S")
                print(f"[{timestamp_str}] Turn {idx}/{len(conversation)} [Channel {channel}] {actual_speaker}:")
                print(f"   \"{speech_text}\"\n")

                payload = {
                    "channel": channel,
                    "speaker_hint": actual_speaker,
                    "text_hint": speech_text,
                    "audio_base64": dummy_b64,
                    "timestamp_ms": time.time() * 1000,
                    "language": "hi" if is_hindi else "en",
                }
                await ws.send(json.dumps(payload))
                await asyncio.sleep(3.5)

            print(f"[Knowra Companion] Finished live simulation conversation.")
            print(f"[Knowra Companion] Check your browser window to view live updates and final recap!\n")
    except Exception as e:
        print(f"[Error] Failed to connect or stream: {e}")


def list_audio_devices():
    """Lists input and output devices available to PyAudio / WASAPI."""
    try:
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            import pyaudio
        p = pyaudio.PyAudio()
        print("\n--- Audio Devices Detected ---")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            is_lb = dev.get("isLoopbackDevice", False)
            lb_tag = " [WASAPI LOOPBACK]" if is_lb else ""
            print(f"[{i}] {dev.get('name')}{lb_tag} (In: {dev.get('maxInputChannels')}, Out: {dev.get('maxOutputChannels')}, Rate: {int(dev.get('defaultSampleRate', 0))}Hz)")
        p.terminate()
        print("------------------------------\n")
    except ImportError:
        print("[Notice] PyAudio not installed. Run: pip install pyaudiowpatch")


async def capture_channel_stream(
    ws,
    stream,
    channel_id: int,
    speaker_name: str,
    input_rate: int = 16000,
    input_channels: int = 1,
    chunk_size: int = 4000,
    speaker_resolver: Optional[Callable[[], Optional[str]]] = None,
    roster_resolver: Optional[Callable[[], List[str]]] = None,
):
    """
    Reads from an audio stream, downsamples/converts to 16kHz Mono PCM,
    applies peak gain normalization + Voice Activity Detection (VAD) energy gating,
    and pushes clean speech chunks to the WebSocket with dynamic speaker attribution.

    Accuracy features:
    - Dynamic speaker resolver: queries Teams UIA / window tracker to attribute turns to real names
    - Peak normalization: boosts quiet audio to -3 dBFS so Whisper receives optimal levels
    - Pre-roll buffer: keeps 2 trailing silence frames as leading context for word boundaries
    - Post-roll buffer: keeps 3 trailing silence frames after speech for syllable ends
    - Max chunk ~4.5s: longer context gives Whisper better word-boundary accuracy
    """
    loop = asyncio.get_event_loop()
    speech_buffer = bytearray()
    silence_counter = 0
    # RMS threshold for speech: values below 220 are ambient silence / background noise
    ENERGY_THRESHOLD = 220.0
    # Target peak amplitude for normalization (~-3 dBFS in int16 range)
    TARGET_PEAK = 23000.0
    # Pre-roll ring buffer: keep last 2 silence frames as leading context
    preroll_ring: list[bytes] = []
    PREROLL_FRAMES = 2

    needs_resample = (input_rate != 16000)
    if needs_resample:
        import math
        g = math.gcd(input_rate, 16000)
        up = 16000 // g
        down = input_rate // g

    try:
        while True:
            data = await loop.run_in_executor(None, stream.read, chunk_size, False)
            if not data:
                await asyncio.sleep(0.005)
                continue

            raw_np = np.frombuffer(data, dtype=np.int16)
            if len(raw_np) == 0:
                await asyncio.sleep(0.005)
                continue

            # 1. Convert to Mono if multi-channel (e.g. 2-channel WASAPI loopback)
            if input_channels == 2:
                mono_np = ((raw_np[0::2].astype(np.int32) + raw_np[1::2].astype(np.int32)) // 2).astype(np.int16)
            elif input_channels > 2:
                mono_np = np.mean(raw_np.reshape(-1, input_channels), axis=1).astype(np.int16)
            else:
                mono_np = raw_np

            # 2. Resample to 16000Hz if needed
            if needs_resample:
                resampled_np = scipy.signal.resample_poly(mono_np, up, down).astype(np.int16)
            else:
                resampled_np = mono_np

            # 3. Calculate raw RMS energy BEFORE any gain normalization to avoid boosting ambient silence
            raw_rms = float(np.sqrt(np.mean(resampled_np.astype(np.float32) ** 2)))

            if raw_rms >= ENERGY_THRESHOLD:
                # Active speech: apply peak normalization for optimal Whisper recognition
                peak = float(np.max(np.abs(resampled_np)))
                if peak > 0:
                    gain = min(TARGET_PEAK / peak, 8.0)
                    if gain > 1.05:
                        resampled_np = np.clip(resampled_np.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
                pcm_16k_bytes = resampled_np.tobytes()

                # Prepend pre-roll context on speech onset
                if len(speech_buffer) == 0:
                    for preroll_frame in preroll_ring:
                        speech_buffer.extend(preroll_frame)
                    preroll_ring.clear()
                speech_buffer.extend(pcm_16k_bytes)
                silence_counter = 0
            else:
                # Silence / ambient frame - do NOT amplify noise!
                pcm_16k_bytes = resampled_np.tobytes()
                if len(speech_buffer) > 0:
                    silence_counter += 1
                    # Keep a brief trailing post-roll (up to 3 frames) for natural word ends
                    if silence_counter <= 3:
                        speech_buffer.extend(pcm_16k_bytes)
                else:
                    # No active speech: store unamplified frame in pre-roll ring buffer
                    preroll_ring.append(pcm_16k_bytes)
                    if len(preroll_ring) > PREROLL_FRAMES:
                        preroll_ring.pop(0)

            # Flush condition:
            # - Accumulated >= 1.0s (32,000 bytes) and speaker paused (silence_counter >= 5)
            # - OR accumulated max chunk >= ~4.5s (144,000 bytes)
            has_enough_speech = len(speech_buffer) >= 32000
            reached_max_chunk = len(speech_buffer) >= 144000
            speaker_paused = (silence_counter >= 5 and has_enough_speech)

            if reached_max_chunk or speaker_paused:
                chunk_to_send = bytes(speech_buffer)
                speech_buffer.clear()
                silence_counter = 0

                # Strict buffer validation: ensure the entire chunk contains genuine voice energy
                buf_samples = np.frombuffer(chunk_to_send, dtype=np.int16)
                if len(buf_samples) > 0:
                    buf_rms = float(np.sqrt(np.mean(buf_samples.astype(np.float32) ** 2)))
                    if buf_rms < 260.0:
                        # Chunk was mostly trailing noise or quiet clicks; discard instead of sending phantom turn
                        continue

                # Resolve dynamic speaker name and roster
                current_speaker = speaker_resolver() if speaker_resolver else (speaker_name if channel_id == 1 else None)
                known_roster = roster_resolver() if roster_resolver else None

                b64_audio = base64.b64encode(chunk_to_send).decode("utf-8")
                payload = {
                    "channel": channel_id,
                    "speaker_hint": current_speaker,
                    "audio_base64": b64_audio,
                    "timestamp_ms": time.time() * 1000,
                }
                if known_roster:
                    payload["roster_hint"] = known_roster

                await ws.send(json.dumps(payload))

                duration_sec = round(len(chunk_to_send) / 32000.0, 1)
                timestamp_str = time.strftime("%H:%M:%S")
                ch_icon = "🎙️ [Your Mic]" if channel_id == 1 else "🔊 [Teams Audio]"
                disp_tag = current_speaker or (speaker_name if channel_id == 1 else "Multi-Speaker Loopback")
                print(f"[{timestamp_str}] {ch_icon} {disp_tag}: Spoke {duration_sec}s (Energy: {int(buf_rms)}) -> Transcribing...")

            elif len(speech_buffer) > 0 and silence_counter > 8:
                # Drop short background pop/click (< 1.0s) followed by prolonged silence
                speech_buffer.clear()
                silence_counter = 0

            await asyncio.sleep(0.005)
    except asyncio.CancelledError:
        pass


async def run_hardware_capture(
    ws_url: str,
    meeting_id: str,
    language: str = "hi",
    host_name: str = "Sujal Nage",
    remote_name: str = "Remote Attendee",
    attendees: str = "",
):
    """
    Captures live hardware:
      - Channel 1: Host Microphone (16kHz mono, attributed to host_name)
      - Channel 2: Teams.exe audio via Windows WASAPI Loopback (resampled to 16kHz mono)
      - Teams Live Attendee & Active Speaker Tracker: detects real participant names via UIA & window inspection
    """
    # Initialize live attendee tracker with individually parsed attendee names
    initial_roster: List[str] = []
    import re
    if attendees:
        for item in re.split(r",| and | & ", attendees):
            clean_item = clean_person_name(item)
            if clean_item and is_valid_person_name(clean_item, host_name=host_name):
                if clean_item not in initial_roster:
                    initial_roster.append(clean_item)
    if remote_name and remote_name != "Remote Attendee":
        for item in re.split(r",| and | & ", remote_name):
            clean_item = clean_person_name(item)
            if clean_item and is_valid_person_name(clean_item, host_name=host_name):
                if clean_item not in initial_roster:
                    initial_roster.append(clean_item)

    tracker = TeamsLiveAttendeeTracker(initial_attendees=initial_roster, host_name=host_name)
    tracker.start()

    print(f"\n========================================================")
    print(f" Knowra Desktop Companion - Real Live Teams Capture")
    print(f" Meeting ID : {meeting_id}")
    print(f" Server WS  : {ws_url}")
    print(f" Language   : {'Hindi (हिंदी)' if language == 'hi' else 'English'}")
    print(f" Host Name  : {host_name} (Channel 1 - Local Mic)")
    attendee_display = ", ".join(tracker.known_roster) if tracker.known_roster else "Auto-detecting via Teams UI"
    print(f" Attendee(s): {attendee_display} (Channel 2 - Teams)")
    print(f" Teams Sync : ACTIVE (Real-time UIA Active Speaker & Roster Tracker)")
    print(f" Mode       : REAL HARDWARE (Microphone + Teams Loopback)")
    print(f" VAD Filter : ACTIVE (Auto-skips background silence)")
    print(f"========================================================\n")

    try:
        try:
            import pyaudiowpatch as pyaudio
            has_loopback_support = True
        except ImportError:
            import pyaudio
            has_loopback_support = False
    except ImportError:
        print("\n[Notice] PyAudio is not installed.")
        print("To capture live hardware on Windows, install: pip install pyaudiowpatch")
        print("Falling back to rich multi-speaker simulation mode...\n")
        await run_simulation(ws_url, meeting_id, language, host_name=host_name)
        tracker.stop()
        return

    p = pyaudio.PyAudio()
    mic_stream = None
    loopback_stream = None
    lb_rate = 48000
    lb_channels = 2

    try:
        # 1. Open Host Microphone (Channel 1)
        mic_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000,
        )
        print(f"[Audio] [Channel 1] Host Microphone connected ({host_name}).")

        # 2. Search for Windows WASAPI loopback device for Teams output (Channel 2)
        if has_loopback_support:
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                if not default_speakers["isLoopbackDevice"]:
                    for loopback in p.get_loopback_device_info_generator():
                        if default_speakers["name"] in loopback["name"]:
                            default_speakers = loopback
                            break

                lb_channels = int(default_speakers.get("maxInputChannels", 2))
                lb_rate = int(default_speakers.get("defaultSampleRate", 48000))
                loopback_stream = p.open(
                    format=pyaudio.paInt16,
                    channels=lb_channels,
                    rate=lb_rate,
                    input=True,
                    input_device_index=default_speakers["index"],
                    frames_per_buffer=4000,
                )
                print(f"[Audio] [Channel 2] Teams.exe Loopback connected ({default_speakers['name']} @ {lb_rate}Hz, {lb_channels}ch -> Downsampling to 16kHz mono).")
            except Exception as le:
                print(f"[Audio] Note: System loopback device not opened ({le}). Capturing Channel 1 only.")
        else:
            print("[Audio] Note: Install 'pyaudiowpatch' to enable automated Teams.exe system audio loopback.")

        print(f"\n[Knowra Companion] Connecting live audio stream to {ws_url}...")
        try:
            async with websockets.connect(ws_url) as ws:
                print("[Knowra Companion] Connected! Capturing meeting audio. Speak in your mic or Teams call.")
                print("[Knowra Companion] Press Ctrl+C at any time to stop.\n")
                tasks = [
                    asyncio.create_task(
                        capture_channel_stream(
                            ws=ws,
                            stream=mic_stream,
                            channel_id=1,
                            speaker_name=host_name,
                            input_rate=16000,
                            input_channels=1,
                        )
                    )
                ]
                if loopback_stream:
                    tasks.append(
                        asyncio.create_task(
                            capture_channel_stream(
                                ws=ws,
                                stream=loopback_stream,
                                channel_id=2,
                                speaker_name=remote_name,
                                input_rate=lb_rate,
                                input_channels=lb_channels,
                                speaker_resolver=tracker.get_active_speaker_hint,
                                roster_resolver=tracker.get_known_roster,
                            )
                        )
                    )

                try:
                    await asyncio.gather(*tasks)
                except KeyboardInterrupt:
                    print("\n[Knowra Companion] Stopped live meeting capture.")
                finally:
                    for t in tasks:
                        t.cancel()
        except Exception as conn_err:
            print(f"\n[Connection Error] Could not connect to live meeting stream: {conn_err}")
            print("Please ensure:")
            print("  1. Backend is running: uvicorn app.main:app --reload")
            print("  2. You clicked 'Start Live Session' in the browser to initialize this meeting ID first.\n")
    finally:
        tracker.stop()
        if mic_stream:
            mic_stream.stop_stream()
            mic_stream.close()
        if loopback_stream:
            loopback_stream.stop_stream()
            loopback_stream.close()
        p.terminate()


class DesktopAgentController:
    """
    Manages the lifecycle of live hardware audio capture on behalf of the browser.
    Runs capture asynchronously in a dedicated event loop thread.
    """

    def __init__(self, host_name: str = "Sujal Nage", server_base: str = "http://127.0.0.1:8000"):
        self.host_name = host_name
        self.server_base = server_base
        self.active_meeting_id: Optional[str] = None
        self.capture_thread: Optional[threading.Thread] = None
        self.capture_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_capturing = False
        self._lock = threading.Lock()

    def start_capture(
        self,
        meeting_id: str,
        host_name: Optional[str] = None,
        attendees: str = "",
        language: str = "hi",
        server: Optional[str] = None,
    ) -> bool:
        with self._lock:
            if self.is_capturing and self.active_meeting_id == meeting_id:
                return True
            self.stop_capture_internal()

            self.active_meeting_id = meeting_id
            effective_host = host_name or self.host_name
            effective_server = server or self.server_base
            ws_url = f"{effective_server.replace('http://', 'ws://').replace('https://', 'wss://')}/api/v1/meetings/{meeting_id}/live-stream"

            def runner():
                self.capture_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.capture_loop)
                self.is_capturing = True
                print(f"\n[Knowra Agent] 🚀 1-Click Launch received from browser for meeting {meeting_id}!")
                print(f"[Knowra Agent] Host: {effective_host} | Attendees: {attendees or 'Auto-Detect via Teams'}\n")
                try:
                    self.capture_loop.run_until_complete(
                        run_hardware_capture(
                            ws_url=ws_url,
                            meeting_id=meeting_id,
                            language=language,
                            host_name=effective_host,
                            remote_name="Remote Attendee",
                            attendees=attendees,
                        )
                    )
                except Exception as e:
                    print(f"[Knowra Agent] Capture finished or stopped: {e}")
                finally:
                    self.is_capturing = False
                    self.active_meeting_id = None
                    print("[Knowra Agent] Ready for next 1-click meeting launch.\n")

            self.capture_thread = threading.Thread(target=runner, daemon=True)
            self.capture_thread.start()
            return True

    def stop_capture(self) -> bool:
        with self._lock:
            return self.stop_capture_internal()

    def stop_capture_internal(self) -> bool:
        if self.capture_loop and self.capture_loop.is_running():
            for task in asyncio.all_tasks(self.capture_loop):
                self.capture_loop.call_soon_threadsafe(task.cancel)
            self.is_capturing = False
            self.active_meeting_id = None
            return True
        self.is_capturing = False
        self.active_meeting_id = None
        return False

    def get_status(self) -> dict:
        with self._lock:
            return {
                "status": "CAPTURING" if self.is_capturing else "READY",
                "activeMeetingId": self.active_meeting_id,
                "hostName": self.host_name,
                "agentVersion": "1.0.0",
                "port": 9876,
            }


def make_agent_handler(controller: DesktopAgentController):
    class AgentHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress default access logs

        def _send_cors_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self):
            if self.path.startswith("/status"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(controller.get_status()).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path.startswith("/start"):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len) if content_len > 0 else b"{}"
                data = json.loads(body.decode("utf-8")) if body else {}

                meeting_id = data.get("meetingId") or data.get("meeting_id")
                if not meeting_id:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "meetingId is required"}).encode("utf-8"))
                    return

                controller.start_capture(
                    meeting_id=str(meeting_id),
                    host_name=data.get("hostName") or data.get("host_name"),
                    attendees=data.get("attendees", ""),
                    language=data.get("language", "hi"),
                    server=data.get("server") or data.get("serverUrl"),
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "CAPTURING", "meetingId": str(meeting_id)}).encode("utf-8"))

            elif self.path.startswith("/stop"):
                controller.stop_capture()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "STOPPED"}).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

    return AgentHandler


def run_agent_server(port: int = 9876, host_name: str = "Sujal Nage", server_url: str = "http://127.0.0.1:8000"):
    """Starts the persistent background agent listening for 1-click browser triggers."""
    controller = DesktopAgentController(host_name=host_name, server_base=server_url)
    handler = make_agent_handler(controller)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)

    print("\n========================================================")
    print(" Knowra Desktop Agent (1-Click Browser Auto-Launch)")
    print(f" Listening on : http://127.0.0.1:{port}")
    print(f" Host Name    : {host_name} (Channel 1 - Local Mic)")
    print(f" Teams Audio  : Windows WASAPI Loopback (Channel 2)")
    print(f" Status       : READY (Waiting for browser 1-click trigger)")
    print("========================================================\n")
    print("💡 You don't need to touch this terminal anymore!")
    print("Just click 'Start Live Session' in the Knowra web app,")
    print("and audio capture will start and stop automatically.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Agent] Stopping desktop agent server...")
        controller.stop_capture()
        server.server_close()


def main():
    detected_host = detect_host_display_name()
    parser = argparse.ArgumentParser(description="Knowra Desktop Meeting Companion (Method 3)")
    parser.add_argument("--meeting-id", type=str, default="", help="Target meeting UUID (optional; omit to run 1-click agent server)")
    parser.add_argument("--server", type=str, default="http://127.0.0.1:8000", help="Knowra API Server Base URL")
    parser.add_argument("--daemon", action="store_true", help="Run as background agent server on port 9876 for 1-click browser auto-launch")
    parser.add_argument("--agent", action="store_true", help="Alias for --daemon")
    parser.add_argument("--port", type=int, default=9876, help="Local agent server port (default: 9876)")
    parser.add_argument("--simulate", action="store_true", help="Run English simulated conversation")
    parser.add_argument("--hindi", action="store_true", help="Run Hindi / Hinglish simulated conversation")
    parser.add_argument("--language", type=str, default="en", help="Language: 'hi' or 'en'")
    parser.add_argument("--host-name", type=str, default=detected_host, help=f"Host display name (defaults to auto-detected: '{detected_host}')")
    parser.add_argument("--attendees", type=str, default="", help="Comma-separated attendee names (e.g. 'Sarah Jenkins, Alex Rivera')")
    parser.add_argument("--speaker-name", type=str, default="", help="Channel 2 attendee display name")
    parser.add_argument("--list-devices", action="store_true", help="List audio input/output devices")

    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
        return

    # If --daemon, --agent, or no meeting-id provided: start 1-click background agent server!
    if args.daemon or args.agent or (not args.meeting_id and not args.simulate and not args.hindi):
        run_agent_server(port=args.port, host_name=args.host_name, server_url=args.server)
        return

    # Direct meeting capture mode
    ws_base = args.server.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_base}/api/v1/meetings/{args.meeting_id}/live-stream"
    lang = "hi" if args.hindi else args.language
    remote_label = args.speaker_name or (args.attendees if args.attendees else "Remote Attendee")

    if args.simulate or args.hindi:
        asyncio.run(run_simulation(ws_url, args.meeting_id, language=lang, host_name=args.host_name))
    else:
        asyncio.run(
            run_hardware_capture(
                ws_url=ws_url,
                meeting_id=args.meeting_id,
                language=lang,
                host_name=args.host_name,
                remote_name=remote_label,
                attendees=args.attendees,
            )
        )


if __name__ == "__main__":
    main()

