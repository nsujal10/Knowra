import pytest
import uuid
from scripts.desktop_meeting_companion import (
    detect_host_display_name,
    TeamsLiveAttendeeTracker,
    is_valid_person_name,
    clean_person_name,
    extract_conversational_speaker_name,
)


def test_detect_host_display_name(monkeypatch):
    # Test environment variable override
    monkeypatch.setenv("KNOWRA_HOST_NAME", "Alice Enterprise")
    assert detect_host_display_name() == "Alice Enterprise"
    
    # Test fallback
    monkeypatch.delenv("KNOWRA_HOST_NAME", raising=False)
    name = detect_host_display_name()
    assert isinstance(name, str)
    assert len(name) > 0
    assert name in ("Sujal Nage", "sujal.nage") or len(name) > 1


def test_teams_attendee_tracker_roster_and_active_speaker():
    tracker = TeamsLiveAttendeeTracker(
        initial_attendees=["Sarah Jenkins", "Alex Rivera"],
        host_name="Sujal Nage"
    )
    # Initial speaker defaults to first in roster
    assert tracker.get_current_speaker() == "Sarah Jenkins"

    # Active speaker identified
    tracker.set_active_speaker("Alex Rivera (Guest)")
    assert tracker.get_current_speaker() == "Alex Rivera"

    # New attendee joins
    added = tracker.add_attendee("Priya Sharma (External)")
    assert added is True
    assert "Priya Sharma" in tracker.known_roster

    # Noise names ignored
    assert tracker.add_attendee("You") is False
    assert tracker.add_attendee("Sujal Nage") is False
    assert tracker.add_attendee("") is False

    # Setting new active speaker
    tracker.set_active_speaker("Priya Sharma")
    assert tracker.get_current_speaker() == "Priya Sharma"


def test_is_valid_person_name_corporate_filtering():
    # Valid real human names
    assert is_valid_person_name("Harshita") is True
    assert is_valid_person_name("Harshita Baghel") is True
    assert is_valid_person_name("Yash Lade") is True
    assert is_valid_person_name("Rahul Sharma") is True
    assert is_valid_person_name("Alex Morgan") is True
    assert is_valid_person_name("Priya Verma") is True

    # Pronouns, contractions, slang & conversational noise must be rejected
    assert is_valid_person_name("Your") is False
    assert is_valid_person_name("Gonna") is False
    assert is_valid_person_name("Your daughter") is False
    assert is_valid_person_name("Gonna system") is False
    assert is_valid_person_name("System setup") is False
    assert is_valid_person_name("Audible") is False
    assert is_valid_person_name("Ready") is False

    # Corporate / Tenant names must be rejected
    assert is_valid_person_name("Systematix Infotech Pvt Ltd") is False
    assert is_valid_person_name("Softude") is False
    assert is_valid_person_name("Microsoft Teams") is False
    assert is_valid_person_name("Gets 2026") is False  # channel with year/number
    assert is_valid_person_name("sujal.nage@softude.com") is False  # email
    assert is_valid_person_name("Chat") is False  # navigation tab
    assert is_valid_person_name("Calls") is False
    assert is_valid_person_name("Calendar") is False

    # Teams / Zoom UI controls & views must be rejected
    assert is_valid_person_name("Meeting compact view") is False
    assert is_valid_person_name("Compact view") is False
    assert is_valid_person_name("Meeting controls") is False
    assert is_valid_person_name("Breakout room") is False
    assert is_valid_person_name("Together mode") is False

    # Host name must be rejected for remote attendees
    assert is_valid_person_name("Sujal Nage", host_name="Sujal Nage") is False


def test_extract_conversational_speaker_name():
    # English intros
    assert extract_conversational_speaker_name("My name is Harshita.") == "Harshita"
    assert extract_conversational_speaker_name("Harshita, that is my name.") == "Harshita"
    assert extract_conversational_speaker_name("Harshita is my name.") == "Harshita"
    assert extract_conversational_speaker_name("Hello, hello. My name is Harshita.") == "Harshita"
    assert extract_conversational_speaker_name("I am Harshita here.") == "Harshita"
    assert extract_conversational_speaker_name("This is Harshita speaking.") == "Harshita"
    assert extract_conversational_speaker_name("Hi everyone, my name is Rahul Sharma.") == "Rahul Sharma"
    assert extract_conversational_speaker_name("Call me Harshita.") == "Harshita"
    assert extract_conversational_speaker_name("It's Harshita here.") == "Harshita"
    assert extract_conversational_speaker_name("Hi, Yash here.") == "Yash"

    # Hindi / Hinglish intros
    assert extract_conversational_speaker_name("Mera naam Harshita hai.") == "Harshita"
    assert extract_conversational_speaker_name("Main Harshita bol rahi hoon.") == "Harshita"

    # Crucial real-world false positives: conversational speech must return None!
    assert extract_conversational_speaker_name("You're saying it, but it's your name. I'm saying it, but it's my name.") is None
    assert extract_conversational_speaker_name("I'm gonna system setup over here.") is None
    assert extract_conversational_speaker_name("Hello, hello. Oh, your daughter is...") is None
    assert extract_conversational_speaker_name("Because Yash always rocks. Because Yash always rocks.") is None
    assert extract_conversational_speaker_name("That is my name.") is None
    assert extract_conversational_speaker_name("Am I audible?") is None
    assert extract_conversational_speaker_name("I am audible?") is None
    assert extract_conversational_speaker_name("I am ready.") is None
    assert extract_conversational_speaker_name("I can't remember your name.") is None
    assert extract_conversational_speaker_name("I'm going to come to the loopback.") is None
    assert extract_conversational_speaker_name("Goodbye, everyone.") is None

    # Testing with known call roster
    roster = ["Harshita Baghel", "Yash Lade"]
    assert extract_conversational_speaker_name("My name is Harshita.", roster=roster) == "Harshita Baghel"
    assert extract_conversational_speaker_name("Hi, Yash here.", roster=roster) == "Yash Lade"
    assert extract_conversational_speaker_name("This is Yash speaking.", roster=roster) == "Yash Lade"
    assert extract_conversational_speaker_name("You're saying it, but it's your name.", roster=roster) is None
    assert extract_conversational_speaker_name("I'm gonna system setup over here.", roster=roster) is None


def test_teams_attendee_tracker_multi_person_comma_parsing():
    # Test comma-separated string passed in initial_attendees
    tracker = TeamsLiveAttendeeTracker(
        initial_attendees=["Harshita, Yash Lade, Rahul Sharma"],
        host_name="Sujal Nage"
    )
    assert len(tracker.known_roster) == 3
    assert "Harshita" in tracker.known_roster
    assert "Yash Lade" in tracker.known_roster
    assert "Rahul Sharma" in tracker.known_roster


def test_live_acoustic_diarizer_three_or_more_attendees():
    import numpy as np
    from app.services.live_meeting_service import LiveAcousticDiarizer

    sr = 16000
    t = np.linspace(0, 1.5, int(1.5 * sr), endpoint=False)
    def make_pcm(f0, formants):
        sig = np.sin(2 * np.pi * f0 * t) * 15000
        for f, a in formants:
            sig += np.sin(2 * np.pi * f * t) * a
        return sig.astype(np.int16).tobytes()

    pcm_harshita = make_pcm(240, [(480, 8000), (1900, 5000)])
    pcm_yash = make_pcm(155, [(310, 8000), (1200, 6000)])
    pcm_rahul = make_pcm(105, [(210, 9000), (850, 6000)])

    roster = ["Harshita", "Yash Lade", "Rahul Sharma"]
    diarizer = LiveAcousticDiarizer(roster=roster, host_name="Sujal Nage")

    # Turn 1: Harshita speaks
    spk1, is_new1 = diarizer.identify_speaker(pcm_harshita)
    assert spk1 == "Harshita"

    # Turn 2: Yash speaks -> Should be detected as a new distinct speaker cluster!
    spk2, is_new2 = diarizer.identify_speaker(pcm_yash)
    assert spk2 == "Yash Lade"
    assert is_new2 is True

    # Turn 3: Rahul speaks -> Should be detected as a third distinct speaker cluster!
    spk3, is_new3 = diarizer.identify_speaker(pcm_rahul)
    assert spk3 == "Rahul Sharma"
    assert is_new3 is True

    # Turn 4: Harshita speaks again -> Must match Harshita!
    spk4, is_new4 = diarizer.identify_speaker(pcm_harshita)
    assert spk4 == "Harshita"
    assert is_new4 is False

    # Turn 5: Rahul speaks again -> Must match Rahul Sharma!
    spk5, is_new5 = diarizer.identify_speaker(pcm_rahul)
    assert spk5 == "Rahul Sharma"
    assert is_new5 is False

    # Turn 6: Yash speaks again -> Must match Yash Lade!
    spk6, is_new6 = diarizer.identify_speaker(pcm_yash)
    assert spk6 == "Yash Lade"
    assert is_new6 is False


def test_host_conversational_addressing_routes_next_speaker():
    import numpy as np
    from app.services.live_meeting_service import LiveAcousticDiarizer

    sr = 16000
    t = np.linspace(0, 1.5, int(1.5 * sr), endpoint=False)
    pcm_audio = (np.sin(2 * np.pi * 175 * t) * 15000).astype(np.int16).tobytes()

    roster = ["Harshita", "Yash Lade", "Rahul Sharma"]
    diarizer = LiveAcousticDiarizer(roster=roster, host_name="Sujal Nage")

    # Host on Channel 1 addresses Yash
    addressed = diarizer.note_host_addressed_attendee("Yash, what do you think about the API design?")
    assert addressed == "Yash Lade"
    assert diarizer.last_addressed_name == "Yash Lade"

    # Next remote turn on Channel 2 must be attributed to Yash Lade
    spk, _ = diarizer.identify_speaker(pcm_audio)
    assert spk == "Yash Lade"

