import sys
import os
import time
import subprocess
from uuid import UUID, uuid4

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.enums import MediaStatus, ArtifactType
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.models.speaker import Speaker
from app.models.speaker_segment import SpeakerSegment
from app.models.diarization_run import DiarizationRun

Base.metadata.create_all(bind=engine)
import scripts.seed_security
scripts.seed_security.seed()

env = os.environ.copy()
env["ASR_PROVIDER"] = "mock"
env["DIARIZATION_PROVIDER"] = "mock"
env["PYTHONPATH"] = backend_dir

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
    cwd=backend_dir,
    env=env,
)
celery_worker = subprocess.Popen(
    [sys.executable, "-m", "celery", "-A", "app.core.celery_app.celery_app", "worker", "--loglevel=info", "--pool=solo"],
    cwd=backend_dir,
    env=env,
)
for _ in range(20):
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:8000/health", timeout=1) as resp:
            if resp.status == 200:
                print("Server is healthy and ready.")
                break
    except Exception:
        time.sleep(1)
else:
    print("Warning: server health check timed out, proceeding anyway.")


def run_test():
    import requests
    BASE_URL = "http://localhost:8000/api/v1"

    print("\n--- 1. Setup Auth & Meeting ---")
    test_email = f"diarize_{uuid4().hex[:8]}@tenant.com"
    reg_res = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Diarization Tester",
            "organization_name": "Diarization Org",
        },
    )
    assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"

    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    meeting_res = requests.post(
        f"{BASE_URL}/meetings",
        headers=headers,
        json={"title": "Q3 Enterprise Review"},
    )
    assert meeting_res.status_code == 201, f"Create meeting failed: {meeting_res.text}"
    meeting_id = meeting_res.json()["id"]

    me_res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert me_res.status_code == 200, f"Get me failed: {me_res.text}"
    tenant_id = me_res.json()["organization_id"]

    print("\n--- 2. Mock Phase 10 Audio & Phase 11 Transcript ---")
    db = SessionLocal()
    media = MediaAsset(
        tenant_id=UUID(tenant_id),
        meeting_id=UUID(meeting_id),
        filename="executive_session.mp4",
        original_content_type="video/mp4",
        status=MediaStatus.READY,
    )
    db.add(media)
    db.commit()

    artifact = MediaArtifact(
        tenant_id=UUID(tenant_id),
        media_asset_id=media.id,
        artifact_type=ArtifactType.NORMALIZED_AUDIO,
        storage_key="dummy_audio.wav",
        checksum_sha256="dummy_sha256",
        byte_size=1024,
    )
    db.add(artifact)
    db.commit()

    # Provision Phase 11 Canonical Transcript
    transcript = Transcript(
        tenant_id=UUID(tenant_id),
        meeting_id=UUID(meeting_id),
        media_asset_id=media.id,
        language="en",
        duration_seconds=2.0,
        provider_name="mock",
        model_name="mock-asr",
        model_version="1.0",
    )
    db.add(transcript)
    db.flush()

    # Segment 1 (Spoken by SPEAKER_00: 0.0s - 1.0s)
    seg1 = TranscriptSegment(
        tenant_id=UUID(tenant_id),
        transcript_id=transcript.id,
        sequence_number=0,
        start_seconds=0.0,
        end_seconds=1.0,
        text="Hello world",
        confidence=0.99,
    )
    db.add(seg1)
    db.flush()

    w1 = TranscriptWord(
        tenant_id=UUID(tenant_id),
        transcript_segment_id=seg1.id,
        sequence_number=0,
        start_seconds=0.0,
        end_seconds=0.5,
        text="Hello",
        confidence=0.99,
    )
    w2 = TranscriptWord(
        tenant_id=UUID(tenant_id),
        transcript_segment_id=seg1.id,
        sequence_number=1,
        start_seconds=0.5,
        end_seconds=1.0,
        text="world",
        confidence=0.99,
    )
    db.add_all([w1, w2])

    # Segment 2 (Spoken by SPEAKER_01: 1.0s - 2.0s)
    seg2 = TranscriptSegment(
        tenant_id=UUID(tenant_id),
        transcript_id=transcript.id,
        sequence_number=1,
        start_seconds=1.0,
        end_seconds=2.0,
        text="Good morning team",
        confidence=0.98,
    )
    db.add(seg2)
    db.flush()

    w3 = TranscriptWord(
        tenant_id=UUID(tenant_id),
        transcript_segment_id=seg2.id,
        sequence_number=0,
        start_seconds=1.0,
        end_seconds=1.5,
        text="Good",
        confidence=0.98,
    )
    w4 = TranscriptWord(
        tenant_id=UUID(tenant_id),
        transcript_segment_id=seg2.id,
        sequence_number=1,
        start_seconds=1.5,
        end_seconds=2.0,
        text="team",
        confidence=0.98,
    )
    transcript_id = transcript.id
    db.add_all([w3, w4])
    db.commit()
    db.close()

    # Ensure MinIO has dummy audio file
    from app.storage.minio import get_storage_client
    import tempfile
    storage = get_storage_client()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        tmp_name = tmp.name
    try:
        storage.upload_file("knowra-derived", "dummy_audio.wav", tmp_name, "audio/wav")
    except Exception as e:
        print(f"Notice: MinIO dummy upload skipped/failed (drive quota): {e}")
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

    print("\n--- 3. Trigger Diarization Job ---")
    res = requests.post(f"{BASE_URL}/meetings/{meeting_id}/diarization", headers=headers)
    assert res.status_code == 202, f"Queue diarization failed: {res.text}"
    job_id = res.json()["job_id"]
    print(f"Queued diarization job_id: {job_id}")

    print("\n--- 4. Polling for Diarization Completion ---")
    status = None
    for _ in range(25):
        poll_res = requests.get(f"{BASE_URL}/meetings/{meeting_id}/diarization", headers=headers)
        if poll_res.status_code == 200:
            status = poll_res.json()
            print(f"Status: {status['status']}")
            if status['status'] == "COMPLETED":
                break
            elif status['status'] == "FAILED":
                print(f"Job Failed: {status}")
                break
        time.sleep(2)

    assert status is not None and status["status"] == "COMPLETED", f"Expected COMPLETED, got {status}"

    print("\n--- 5. Validate Speaker Entities & Decoupled Timelines ---")
    db = SessionLocal()
    speakers = db.query(Speaker).filter(Speaker.meeting_id == UUID(meeting_id)).all()
    print(f"Found {len(speakers)} speakers in meeting:")
    for spk in speakers:
        print(f"  - [{spk.speaker_label}] Display: '{spk.display_name}', ID: {spk.id}")
    assert len(speakers) == 2, f"Expected 2 speakers, found {len(speakers)}"

    speaker_segments = db.query(SpeakerSegment).filter(SpeakerSegment.tenant_id == UUID(tenant_id)).all()
    print(f"Found {len(speaker_segments)} speaker segments in parallel timeline:")
    for s_seg in speaker_segments:
        print(f"  - Speaker {s_seg.speaker_id}: {s_seg.start_seconds}s -> {s_seg.end_seconds}s (conf: {s_seg.confidence})")
    assert len(speaker_segments) >= 2, "Expected at least 2 speaker segments"

    # Validate TranscriptSegment attribution
    t_segs = db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript_id).order_by(TranscriptSegment.sequence_number).all()
    assert len(t_segs) == 2
    seg1_db, seg2_db = t_segs[0], t_segs[1]

    print(f"\nSegment 1 text='{seg1_db.text}': Speaker={seg1_db.speaker_id}, Conf={seg1_db.alignment_confidence}, Status={seg1_db.alignment_status}")
    print(f"Segment 2 text='{seg2_db.text}': Speaker={seg2_db.speaker_id}, Conf={seg2_db.alignment_confidence}, Status={seg2_db.alignment_status}")

    assert seg1_db.speaker_id is not None, "Segment 1 speaker_id should be assigned"
    assert seg1_db.alignment_status == "ATTRIBUTED"
    assert seg1_db.alignment_confidence == 1.0

    assert seg2_db.speaker_id is not None, "Segment 2 speaker_id should be assigned"
    assert seg2_db.alignment_status == "ATTRIBUTED"
    assert seg2_db.alignment_confidence == 1.0

    # Ensure original ASR text was NOT mutated (Decoupled timeline invariant)
    assert seg1_db.text == "Hello world"
    assert seg2_db.text == "Good morning team"

    # Identify speaker for renaming
    target_speaker_id = str(speakers[0].id)
    db.close()

    print("\n--- 6. Test Speaker Rename PATCH API ---")
    rename_res = requests.patch(
        f"{BASE_URL}/speakers/{target_speaker_id}",
        headers=headers,
        json={"display_name": "Alice Executive"},
    )
    assert rename_res.status_code == 200, f"Rename failed: {rename_res.text}"
    updated_speaker = rename_res.json()
    assert updated_speaker["display_name"] == "Alice Executive"
    print(f"Speaker successfully renamed to '{updated_speaker['display_name']}'")

    print("\n--- 7. Validate Speaker-Attributed Transcript API ---")
    diarized_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/transcript/diarized",
        headers=headers,
    )
    assert diarized_res.status_code == 200, f"Get diarized transcript failed: {diarized_res.text}"
    diarized_data = diarized_res.json()

    print(f"Retrieved diarized transcript: {len(diarized_data['segments'])} segments, {len(diarized_data['speakers'])} speakers")
    assert len(diarized_data["segments"]) == 2
    assert len(diarized_data["speakers"]) == 2

    first_segment = diarized_data["segments"][0]
    print(f"First Segment -> Speaker: '{first_segment['speaker_name']}' ({first_segment['speaker_label']}), Alignment: {first_segment['alignment_status']}")
    assert first_segment["speaker_name"] is not None
    assert first_segment["speaker_label"] is not None
    assert first_segment["alignment_status"] == "ATTRIBUTED"

    print("\n[PASS] Phase 12 Full Workflow Verified Successfully.")


try:
    run_test()
finally:
    print("\n--- Cleaning up background processes ---")
    server.terminate()
    try:
        server.wait(timeout=5)
    except Exception:
        server.kill()
    celery_worker.terminate()
    try:
        celery_worker.wait(timeout=5)
    except Exception:
        celery_worker.kill()
