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

Base.metadata.create_all(bind=engine)
import scripts.seed_security
scripts.seed_security.seed()

env = os.environ.copy()
env["ASR_PROVIDER"] = "mock"
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
time.sleep(5)


def run_test():
    import requests
    BASE_URL = "http://localhost:8000/api/v1"
    
    print("\n--- 1. Setup Auth & Meeting ---")
    test_email = f"trans_{uuid4().hex[:8]}@tenant.com"
    reg_res = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": test_email, "password": "Password123!", "full_name": "T", "organization_name": "Org T"}
    )
    assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
    
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": test_email, "password": "Password123!"}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    
    meeting_res = requests.post(
        f"{BASE_URL}/meetings",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "ASR Test"}
    )
    assert meeting_res.status_code == 201, f"Create meeting failed: {meeting_res.text}"
    meeting_id = meeting_res.json()["id"]
    
    me_res = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200, f"Get me failed: {me_res.text}"
    tenant_id = me_res.json()["organization_id"]
    
    print("\n--- 2. Mock Phase 10 Artifact Generation ---")
    db = SessionLocal()
    media = MediaAsset(
        tenant_id=UUID(tenant_id),
        meeting_id=UUID(meeting_id),
        filename="test.mp4",
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
        checksum_sha256="dummy",
        byte_size=1024,
    )
    db.add(artifact)
    db.commit()
    db.close()
    
    # Write a dummy wav to minio so download doesn't fail
    from app.storage.minio import get_storage_client
    import tempfile
    storage = get_storage_client()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        tmp_name = tmp.name
    try:
        storage.upload_file("knowra-derived", "dummy_audio.wav", tmp_name, "audio/wav")
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    
    print("\n--- 3. Trigger Transcription Job ---")
    res = requests.post(f"{BASE_URL}/meetings/{meeting_id}/transcription", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 202, f"Queue transcription failed: {res.text}"
    job_id = res.json()["job_id"]
    print(f"Queued job_id: {job_id}")
    
    print("\n--- 4. Polling for Completion ---")
    status = None
    for _ in range(25):
        poll_res = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcription", headers={"Authorization": f"Bearer {token}"})
        if poll_res.status_code == 200:
            status = poll_res.json()
            print(f"Status: {status['status']}")
            if status['status'] == "COMPLETED":
                break
            elif status['status'] == "FAILED":
                print(f"Job Failed: {status}")
                break
        else:
            print(f"Polling HTTP {poll_res.status_code}: {poll_res.text}")
        time.sleep(2)
        
    assert status is not None and status['status'] == "COMPLETED", f"Expected COMPLETED, got {status}"
    
    print("\n--- 5. Validate Output Transcript ---")
    trans_res = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcript", headers={"Authorization": f"Bearer {token}"})
    assert trans_res.status_code == 200, f"Get transcript failed: {trans_res.text}"
    transcript = trans_res.json()
    print(f"Got transcript! ID: {transcript['id']}, Language: {transcript['language']}")
    assert len(transcript['segments']) > 0, "No segments in transcript"
    assert transcript['segments'][0]['text'] == "Hello world"
    print("\n[PASS] Phase 11 Full Workflow Verified.")


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
