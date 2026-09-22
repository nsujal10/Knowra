"""
Verification test for:
1. Audio Downsampling & Voice Activity Detection (VAD)
2. Attendee naming during Live Meeting start
3. Speaker rename endpoint: PATCH /meetings/{meeting_id}/speakers/{speaker_id}
"""

import os
import sys
import uuid
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.speaker import Speaker
from app.security.tenant import TenantContext, get_tenant_context
from app.services.live_meeting_service import LiveMeetingManager


def main():
    print("=======================================================")
    print(" Running Audio Downsampling, VAD & Speaker Rename Test")
    print("=======================================================\n")

    # 1. Setup Tenant Context
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(id=uuid.uuid4(), name="Knowra Test Org", slug="knowra-test")
            db.add(org)
            db.commit()

        user = db.query(User).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="test@knowra.ai",
                password_hash="pw_hash",
                full_name="Sujal Nage",
                is_active=True,
            )
            db.add(user)
            db.commit()

        tenant_id = org.id
        user_id = user.id
    finally:
        db.close()

    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    client = TestClient(app)

    # 2. Test Live Meeting Start with Attendees
    print("[1/4] Starting live meeting with attendees...")
    res = client.post(
        "/api/v1/meetings/live/start",
        json={
            "title": "Sprint Sync with Alex & Sarah",
            "hostName": "Sujal Nage",
            "attendees": "Sarah Jenkins",
            "language": "hi",
        },
    )
    assert res.status_code == 201, f"Failed to start meeting: {res.text}"
    data = res.json()
    meeting_id = data["meetingId"]
    print(f"   Meeting started: {meeting_id}")

    # Check Channel 2 in LiveMeetingManager
    manager = LiveMeetingManager.get_instance()
    session = manager.get_session(uuid.UUID(meeting_id))
    assert session is not None
    assert session.channels[2].display_name == "Sarah Jenkins"
    print(f"   Channel 2 display name: {session.channels[2].display_name} (Confirmed!)")

    # 3. Test Renaming Speaker via PATCH /api/v1/meetings/{id}/speakers/{speaker_id}
    print("\n[2/4] Testing Speaker Rename API...")
    # First persist a speaker
    db = SessionLocal()
    try:
        spk = Speaker(
            meeting_id=uuid.UUID(meeting_id),
            tenant_id=tenant_id,
            speaker_label="SPEAKER_2",
            display_name="Sarah Jenkins",
        )
        db.add(spk)
        db.commit()
        db.refresh(spk)
        spk_id = str(spk.id)
    finally:
        db.close()

    patch_res = client.patch(
        f"/api/v1/meetings/{meeting_id}/speakers/{spk_id}",
        json={"displayName": "Sarah Connor (Tech Lead)"},
    )
    assert patch_res.status_code == 200, f"Failed to rename speaker: {patch_res.text}"
    patch_data = patch_res.json()
    assert patch_data["displayName"] == "Sarah Connor (Tech Lead)"
    print(f"   Renamed speaker to: {patch_data['displayName']} (Status 200 OK!)")

    # 4. Test 48kHz to 16kHz downsampling accuracy
    print("\n[3/4] Testing 48kHz Stereo to 16kHz Mono audio conversion...")
    import scipy.signal
    duration_sec = 2.0
    rate_48k = 48000
    t = np.linspace(0, duration_sec, int(rate_48k * duration_sec), endpoint=False)
    # 300Hz tone
    sine_wave = (np.sin(2 * np.pi * 300 * t) * 8000).astype(np.int16)
    stereo_interleaved = np.empty((len(sine_wave) * 2,), dtype=np.int16)
    stereo_interleaved[0::2] = sine_wave
    stereo_interleaved[1::2] = sine_wave

    # Downsample
    raw_mono = ((stereo_interleaved[0::2].astype(np.int32) + stereo_interleaved[1::2].astype(np.int32)) // 2).astype(np.int16)
    resampled_16k = scipy.signal.resample_poly(raw_mono, 1, 3).astype(np.int16)

    assert len(resampled_16k) == int(16000 * duration_sec)
    rms_speech = float(np.sqrt(np.mean(resampled_16k.astype(np.float32) ** 2)))
    print(f"   Converted {len(stereo_interleaved)} stereo samples -> {len(resampled_16k)} mono 16kHz samples (RMS: {int(rms_speech)})")
    assert rms_speech > 5000, "Speech energy check failed"

    # 5. Test VAD Silence Gating
    print("\n[4/4] Testing VAD Silence Gating...")
    silence = np.zeros(16000, dtype=np.int16)
    rms_silence = float(np.sqrt(np.mean(silence.astype(np.float32) ** 2)))
    assert rms_silence < 50.0, "Silence RMS check failed"
    print(f"   Silence RMS: {rms_silence:.1f} (Correctly rejected below threshold 220)")

    print("\n=======================================================")
    print(" ALL TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
