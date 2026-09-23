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


def test_live_acoustic_diarizer_comma_separated_roster_input():
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

    # Passing comma-separated string as a single item (as happens in browser input or modal)
    diarizer = LiveAcousticDiarizer(
        roster=["Harshita Baghel, Yash Lade, Rahul Sharma"],
        host_name="Sujal Nage"
    )
    assert len(diarizer.roster) == 3
    assert diarizer.roster == ["Harshita Baghel", "Yash Lade", "Rahul Sharma"]

    # Person 1 speaks -> Harshita Baghel
    spk1, _ = diarizer.identify_speaker(pcm_harshita)
    assert spk1 == "Harshita Baghel"

    # Person 2 speaks -> Yash Lade
    spk2, _ = diarizer.identify_speaker(pcm_yash)
    assert spk2 == "Yash Lade"

    # Person 3 speaks -> Rahul Sharma (Person 3 must be detected by name!)
    spk3, _ = diarizer.identify_speaker(pcm_rahul)
    assert spk3 == "Rahul Sharma"


def test_mid_meeting_attendee_addition_not_overwritten_by_existing_member():
    """
    CRITICAL REGRESSION TEST:
    When a person is added mid-meeting, and speaks while a stale hint for an
    existing member is present, the new person MUST NOT be replaced by the existing member!
    """
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

    # Meeting starts with 2 attendees
    diarizer = LiveAcousticDiarizer(
        roster=["Harshita Baghel", "Yash Lade"],
        host_name="Sujal Nage"
    )
    # Turn 1: Harshita speaks
    s1, _ = diarizer.identify_speaker(pcm_harshita)
    assert s1 == "Harshita Baghel"

    # Turn 2: Yash speaks
    s2, _ = diarizer.identify_speaker(pcm_yash)
    assert s2 == "Yash Lade"

    # Mid-meeting: Rahul Sharma is added!
    diarizer.add_to_roster("Rahul Sharma")
    assert "Rahul Sharma" in diarizer.roster

    # Turn 3: Rahul speaks, but the incoming audio chunk still contains stale speaker_hint='Yash Lade'
    s3, is_new3 = diarizer.identify_speaker(pcm_rahul, speaker_hint="Yash Lade")
    # MUST be Rahul Sharma, NEVER Yash Lade!
    assert s3 == "Rahul Sharma"
    assert is_new3 is True

    # Turn 4: Harshita speaks again -> Must still be Harshita Baghel!
    s4, is_new4 = diarizer.identify_speaker(pcm_harshita)
    assert s4 == "Harshita Baghel"
    assert is_new4 is False

    # Turn 5: Yash speaks again -> Must still be Yash Lade!
    s5, is_new5 = diarizer.identify_speaker(pcm_yash)
    assert s5 == "Yash Lade"
    assert is_new5 is False

    # Turn 6: Rahul speaks again -> Must still be Rahul Sharma!
    s6, is_new6 = diarizer.identify_speaker(pcm_rahul)
    assert s6 == "Rahul Sharma"
    assert is_new6 is False


def test_mid_meeting_attendee_addition_reconciles_placeholder_cluster():
    """
    Tests that if a 3rd speaker speaks BEFORE being added to the roster (getting 'Participant 3'),
    and is subsequently added via add_to_roster('Rahul Sharma'), their placeholder cluster
    is automatically renamed and reconciled to 'Rahul Sharma'.
    """
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

    # Meeting starts with 2 attendees
    diarizer = LiveAcousticDiarizer(
        roster=["Harshita Baghel", "Yash Lade"],
        host_name="Sujal Nage"
    )
    diarizer.identify_speaker(pcm_harshita)
    diarizer.identify_speaker(pcm_yash)

    # Unknown 3rd person speaks -> gets assigned 'Participant 3'
    spk3_before, _ = diarizer.identify_speaker(pcm_rahul)
    assert spk3_before == "Participant 3"

    # Now Rahul Sharma is added mid-meeting
    renames = diarizer.add_to_roster("Rahul Sharma")
    assert renames == [("Participant 3", "Rahul Sharma")]

    # Next turn from Rahul must now be recognized as Rahul Sharma
    spk3_after, is_new = diarizer.identify_speaker(pcm_rahul)
    assert spk3_after == "Rahul Sharma"
    assert is_new is False


def test_close_pitch_same_gender_discrimination():
    """
    Tests that two male speakers with nearby fundamental frequencies (e.g. 130Hz vs 110Hz)
    are separated cleanly by the 8-dim RBF pitch + MFCC + formant + centroid embedding
    instead of collapsing into a single cluster.
    """
    import numpy as np
    from app.services.live_meeting_service import LiveAcousticDiarizer, extract_acoustic_embedding

    sr = 16000
    t = np.linspace(0, 1.5, int(1.5 * sr), endpoint=False)

    # Speaker 1: Male 130Hz + harmonics
    s1 = (np.sin(2 * np.pi * 130 * t) + 0.6 * np.sin(2 * np.pi * 260 * t) + 0.3 * np.sin(2 * np.pi * 390 * t)) * 12000
    # Speaker 1 variation (slight pitch drift ~131Hz)
    s1_var = (np.sin(2 * np.pi * 131 * t) + 0.58 * np.sin(2 * np.pi * 262 * t) + 0.32 * np.sin(2 * np.pi * 393 * t)) * 12000
    # Speaker 2: Male 110Hz + harmonics
    s2 = (np.sin(2 * np.pi * 110 * t) + 0.7 * np.sin(2 * np.pi * 220 * t) + 0.4 * np.sin(2 * np.pi * 330 * t)) * 12000

    pcm_s1 = s1.astype(np.int16).tobytes()
    pcm_s1_var = s1_var.astype(np.int16).tobytes()
    pcm_s2 = s2.astype(np.int16).tobytes()

    emb1 = extract_acoustic_embedding(pcm_s1)
    emb1_v = extract_acoustic_embedding(pcm_s1_var)
    emb2 = extract_acoustic_embedding(pcm_s2)

    assert float(np.dot(emb1, emb1_v)) >= 0.95  # Same speaker consistency
    assert float(np.dot(emb1, emb2)) < 0.90     # Different speaker separation

    diarizer = LiveAcousticDiarizer(
        roster=["Yash Lade", "Rahul Sharma"],
        host_name="Sujal Nage"
    )

    spk1, is_new1 = diarizer.identify_speaker(pcm_s1)
    assert spk1 == "Yash Lade"
    assert is_new1 is False

    # Second male speaks -> must NOT collapse into Yash Lade!
    spk2, is_new2 = diarizer.identify_speaker(pcm_s2)
    assert spk2 == "Rahul Sharma"
    assert is_new2 is True

    # First male speaks again -> must match Yash Lade
    spk1_again, is_new1_again = diarizer.identify_speaker(pcm_s1_var)
    assert spk1_again == "Yash Lade"
    assert is_new1_again is False


def test_update_active_cluster_name_does_not_overwrite_confirmed_speaker():
    """
    Tests that if attendee A has an active cluster, and attendee B speaks with a
    conversational self-introduction, attendee A's cluster is NOT overwritten.
    """
    import numpy as np
    from app.services.live_meeting_service import LiveAcousticDiarizer

    sr = 16000
    t = np.linspace(0, 1.5, int(1.5 * sr), endpoint=False)
    pcm_harshita = (np.sin(2 * np.pi * 240 * t) * 15000).astype(np.int16).tobytes()

    diarizer = LiveAcousticDiarizer(
        roster=["Harshita Baghel", "Yash Lade"],
        host_name="Sujal Nage"
    )

    # Harshita speaks first
    diarizer.identify_speaker(pcm_harshita)
    assert diarizer.clusters[diarizer.active_cluster_index].display_name == "Harshita Baghel"

    # Now a turn occurs with self-introduction "Yash Lade"
    old_name = diarizer.update_active_cluster_name("Yash Lade")
    # Must NOT have renamed Harshita's cluster
    assert diarizer.clusters[0].display_name == "Harshita Baghel"
    # Active cluster should now be Yash Lade
    assert diarizer.clusters[diarizer.active_cluster_index].display_name == "Yash Lade"




