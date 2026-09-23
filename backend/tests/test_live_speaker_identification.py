import pytest
import uuid
from scripts.desktop_meeting_companion import (
    detect_host_display_name,
    TeamsLiveAttendeeTracker,
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
