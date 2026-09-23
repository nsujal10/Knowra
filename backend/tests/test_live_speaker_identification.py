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
    assert is_valid_person_name("Rahul Sharma") is True
    assert is_valid_person_name("Alex Morgan") is True
    assert is_valid_person_name("Priya Verma") is True

    # Corporate / Tenant names must be rejected
    assert is_valid_person_name("Systematix Infotech Pvt Ltd") is False
    assert is_valid_person_name("Softude") is False
    assert is_valid_person_name("Microsoft Teams") is False
    assert is_valid_person_name("Gets 2026") is False  # channel with year/number
    assert is_valid_person_name("sujal.nage@softude.com") is False  # email
    assert is_valid_person_name("Chat") is False  # navigation tab
    assert is_valid_person_name("Calls") is False
    assert is_valid_person_name("Calendar") is False

    # Host name must be rejected for remote attendees
    assert is_valid_person_name("Sujal Nage", host_name="Sujal Nage") is False


def test_extract_conversational_speaker_name():
    # English intros
    assert extract_conversational_speaker_name("My name is Harshita.") == "Harshita"
    assert extract_conversational_speaker_name("Hello, hello. My name is Harshita.") == "Harshita"
    assert extract_conversational_speaker_name("I am Harshita here.") == "Harshita"
    assert extract_conversational_speaker_name("This is Harshita speaking.") == "Harshita"
    assert extract_conversational_speaker_name("Hi everyone, my name is Rahul Sharma.") == "Rahul Sharma"

    # Hindi / Hinglish intros
    assert extract_conversational_speaker_name("Mera naam Harshita hai.") == "Harshita"
    assert extract_conversational_speaker_name("Main Harshita bol rahi hoon.") == "Harshita"

    # Non-introduction speech must return None
    assert extract_conversational_speaker_name("Am I audible?") is None
    assert extract_conversational_speaker_name("I am audible?") is None
    assert extract_conversational_speaker_name("I am ready.") is None
    assert extract_conversational_speaker_name("I can't remember your name.") is None
    assert extract_conversational_speaker_name("I'm going to come to the loopback.") is None
    assert extract_conversational_speaker_name("Goodbye, everyone.") is None
