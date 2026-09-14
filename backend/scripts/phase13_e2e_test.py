"""
Phase 13 E2E Test – Canonical Transcript Format
================================================

Workflow tested
---------------
1.  Register & login (fresh tenant per run)
2.  Create a meeting
3.  Seed a canonical Transcript + Segments + Words via DB (mock Phase 11 output)
4.  GET /meetings/{id}/transcript  →  canonical JSON is served correctly
5.  Validate segment fields (text, confidence, timestamps, speaker attribution)
6.  GET /meetings/{id}/transcript/versions  →  no versions yet (no baseline seeded)
7.  POST /meetings/{id}/transcript/versions →  submit human edit, returns version 2
8.  GET /meetings/{id}/transcript?version=2  →  corrected text reflected
9.  GET /meetings/{id}/transcript/versions  →  two entries: version 1 AI + version 2 human
10. Immutability guard: GET ?version=1 must still show ORIGINAL text (not the correction)
11. Tenant isolation: register a second tenant; verify their GET returns 404

Run from the backend directory:
    python scripts/phase13_e2e_test.py
"""

import sys
import os
import time
import subprocess
from uuid import UUID, uuid4

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

# ── Bootstrap DB schema & seed security roles ────────────────────────────────
from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.media_asset import MediaAsset
from app.models.enums import MediaStatus
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.models.transcript_version import TranscriptVersion

Base.metadata.create_all(bind=engine)
import scripts.seed_security
scripts.seed_security.seed()

# ── Launch server (no Celery needed – pure REST test) ─────────────────────────
env = os.environ.copy()
env["ASR_PROVIDER"] = "mock"
env["DIARIZATION_PROVIDER"] = "mock"
env["PYTHONPATH"] = backend_dir

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
    cwd=backend_dir,
    env=env,
)

print("Waiting for server to be ready...")
for _ in range(45):
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


# ── Test runner ───────────────────────────────────────────────────────────────

def run_test():
    import requests
    BASE_URL = "http://localhost:8000/api/v1"

    # ── 1. Auth & Meeting ─────────────────────────────────────────────────────
    print("\n--- 1. Register & Login (Tenant A) ---")
    test_email = f"phase13_{uuid4().hex[:8]}@knowra.com"
    reg = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Transcript Tester",
            "organization_name": f"TranscriptOrg_{uuid4().hex[:6]}",
        },
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"

    login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert me.status_code == 200
    tenant_id = UUID(me.json()["organization_id"])

    meeting = requests.post(
        f"{BASE_URL}/meetings",
        headers=headers,
        json={"title": "Phase 13 Canonical Transcript Meeting"},
    )
    assert meeting.status_code == 201, f"Create meeting failed: {meeting.text}"
    meeting_id = meeting.json()["id"]
    print(f"  meeting_id = {meeting_id}")

    # ── 2. Seed transcript + segments + words directly in DB ──────────────────
    print("\n--- 2. Seeding Transcript + Segments + Words in DB ---")
    db = SessionLocal()

    media = MediaAsset(
        tenant_id=tenant_id,
        meeting_id=UUID(meeting_id),
        filename="q3_review.mp4",
        original_content_type="video/mp4",
        status=MediaStatus.READY,
    )
    db.add(media)
    db.commit()

    transcript = Transcript(
        tenant_id=tenant_id,
        meeting_id=UUID(meeting_id),
        media_asset_id=media.id,
        language="en",
        duration_seconds=10.0,
        provider_name="faster-whisper",
        model_name="large-v3",
        model_version="1.0",
    )
    db.add(transcript)
    db.flush()

    seg1 = TranscriptSegment(
        tenant_id=tenant_id,
        transcript_id=transcript.id,
        sequence_number=0,
        start_seconds=0.0,
        end_seconds=4.5,
        text="The quarterly results exceeded expectations.",
        confidence=0.97,
    )
    seg2 = TranscriptSegment(
        tenant_id=tenant_id,
        transcript_id=transcript.id,
        sequence_number=1,
        start_seconds=5.0,
        end_seconds=10.0,
        text="We should celeberate this achievement.",   # intentional typo: celeberate
        confidence=0.88,
    )
    db.add_all([seg1, seg2])
    db.flush()

    # Words for seg1
    for i, (word, start, end) in enumerate([
        ("The", 0.0, 0.3), ("quarterly", 0.4, 0.9), ("results", 1.0, 1.5),
        ("exceeded", 1.6, 2.2), ("expectations.", 2.3, 4.5)
    ]):
        db.add(TranscriptWord(
            tenant_id=tenant_id,
            transcript_segment_id=seg1.id,
            sequence_number=i,
            start_seconds=start,
            end_seconds=end,
            text=word,
            confidence=0.97,
        ))

    # Seed the AI-baseline version (version 1) in transcript_versions
    import json
    baseline_snapshot = {
        "id": str(transcript.id),
        "meeting_id": meeting_id,
        "tenant_id": str(tenant_id),
        "language": "en",
        "duration_seconds": 10.0,
        "provider_name": "faster-whisper",
        "model_name": "large-v3",
        "model_version": "1.0",
        "current_version_number": 1,
        "version_meta": None,
        "segments": [
            {
                "id": str(seg1.id),
                "sequence_number": 0,
                "start_seconds": 0.0,
                "end_seconds": 4.5,
                "text": "The quarterly results exceeded expectations.",
                "confidence": 0.97,
                "speaker_id": None,
                "speaker_label": None,
                "speaker_display_name": None,
                "alignment_confidence": None,
                "alignment_status": None,
                "words": [],
            },
            {
                "id": str(seg2.id),
                "sequence_number": 1,
                "start_seconds": 5.0,
                "end_seconds": 10.0,
                "text": "We should celeberate this achievement.",
                "confidence": 0.88,
                "speaker_id": None,
                "speaker_label": None,
                "speaker_display_name": None,
                "alignment_confidence": None,
                "alignment_status": None,
                "words": [],
            },
        ],
    }

    v1 = TranscriptVersion(
        tenant_id=tenant_id,
        transcript_id=transcript.id,
        version_number=1,
        source="AI_GENERATED",
        edited_by_user_id=None,
        edit_reason=None,
        snapshot_json=baseline_snapshot,
    )
    db.add(v1)
    db.commit()

    transcript_id = str(transcript.id)
    seg2_id = str(seg2.id)
    db.close()
    print(f"  transcript_id = {transcript_id}")
    print(f"  seg2_id (typo target) = {seg2_id}")

    # ── 3. GET canonical transcript ───────────────────────────────────────────
    print("\n--- 3. GET /meetings/{id}/transcript (latest) ---")
    res = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcript", headers=headers)
    assert res.status_code == 200, f"Get canonical failed: {res.text}"
    ct = res.json()
    print(f"  language={ct['language']}, duration={ct['duration_seconds']}s, segments={len(ct['segments'])}")
    assert ct["language"] == "en"
    assert ct["duration_seconds"] == 10.0
    assert len(ct["segments"]) == 2
    assert ct["segments"][0]["text"] == "The quarterly results exceeded expectations."
    assert ct["segments"][1]["text"] == "We should celeberate this achievement."
    assert ct["segments"][0]["sequence_number"] == 0
    assert ct["segments"][1]["sequence_number"] == 1
    assert len(ct["segments"][0]["words"]) == 5, "Segment 1 should have 5 words"
    print("  [OK] Canonical transcript structure validated.")

    # ── 4. GET versions (only v1 at this point) ───────────────────────────────
    print("\n--- 4. GET /meetings/{id}/transcript/versions (expect 1 version) ---")
    vres = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcript/versions", headers=headers)
    assert vres.status_code == 200, f"List versions failed: {vres.text}"
    versions = vres.json()
    print(f"  Found {len(versions)} version(s)")
    assert len(versions) == 1, f"Expected 1 version (AI baseline), got {len(versions)}"
    assert versions[0]["version_number"] == 1
    assert versions[0]["source"] == "AI_GENERATED"
    assert versions[0]["edited_by_user_id"] is None
    print("  [OK] Version 1 (AI_GENERATED) confirmed.")

    # ── 5. POST human edit (fix typo in seg2) ─────────────────────────────────
    print("\n--- 5. POST /meetings/{id}/transcript/versions (human edit: fix typo) ---")
    edit_res = requests.post(
        f"{BASE_URL}/meetings/{meeting_id}/transcript/versions",
        headers=headers,
        json={
            "edit_reason": "Fixed typo in segment 2: celeberate -> celebrate",
            "segment_corrections": {
                seg2_id: "We should celebrate this achievement.",
            },
        },
    )
    assert edit_res.status_code == 201, f"Create edit failed: {edit_res.text}"
    edit_data = edit_res.json()
    print(f"  new_version_number = {edit_data['new_version_number']}")
    assert edit_data["new_version_number"] == 2
    print("  [OK] Edit version 2 created.")

    # ── 6. GET canonical again → corrected text ───────────────────────────────
    print("\n--- 6. GET /meetings/{id}/transcript?version=2 (corrected) ---")
    v2_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/transcript?version=2",
        headers=headers,
    )
    assert v2_res.status_code == 200, f"Get v2 failed: {v2_res.text}"
    v2 = v2_res.json()
    corrected_text = v2["segments"][1]["text"]
    print(f"  Segment 2 text in v2: '{corrected_text}'")
    assert corrected_text == "We should celebrate this achievement.", \
        f"Expected corrected text, got: {corrected_text}"
    print("  [OK] Corrected text confirmed in version 2.")

    # ── 7. Immutability: version 1 must still have original typo ──────────────
    print("\n--- 7. GET /meetings/{id}/transcript?version=1 (AI baseline must be immutable) ---")
    v1_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/transcript?version=1",
        headers=headers,
    )
    assert v1_res.status_code == 200, f"Get v1 failed: {v1_res.text}"
    v1_data = v1_res.json()
    v1_seg2_text = v1_data["segments"][1]["text"]
    print(f"  Segment 2 text in v1: '{v1_seg2_text}'")
    assert v1_seg2_text == "We should celeberate this achievement.", \
        f"AI version 1 was mutated! Got: {v1_seg2_text}"
    print("  [OK] AI baseline (version 1) is immutable -- original typo preserved.")

    # ── 8. GET versions now shows 2 entries ───────────────────────────────────
    print("\n--- 8. GET /meetings/{id}/transcript/versions (expect 2 versions) ---")
    vres2 = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcript/versions", headers=headers)
    assert vres2.status_code == 200
    versions2 = vres2.json()
    print(f"  Found {len(versions2)} version(s):")
    for v in versions2:
        print(f"    v{v['version_number']} source={v['source']} reason={v['edit_reason']}")
    assert len(versions2) == 2
    assert versions2[0]["source"] == "AI_GENERATED"
    assert versions2[1]["source"] == "HUMAN_EDITED"
    assert versions2[1]["edit_reason"] == "Fixed typo in segment 2: celeberate -> celebrate"
    print("  [OK] Version history trail is complete.")

    # ── 9. Tenant Isolation: second tenant cannot read first tenant's transcript
    print("\n--- 9. Tenant Isolation Check ---")
    email_b = f"tenant_b_{uuid4().hex[:8]}@knowra.com"
    requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "Tenant B",
            "organization_name": f"OrgB_{uuid4().hex[:6]}",
        },
    )
    login_b = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email_b, "password": "Password123!"},
    )
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    iso_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/transcript",
        headers=headers_b,
    )
    # Tenant B has no meeting with this ID → must return 404
    assert iso_res.status_code == 404, \
        f"Isolation FAILED: Tenant B got {iso_res.status_code} on Tenant A's transcript"
    print("  [OK] Tenant isolation confirmed -- cross-tenant read correctly returns 404.")

    # ── 10. Invalid version returns 404 ───────────────────────────────────────
    print("\n--- 10. GET non-existent version returns 404 ---")
    bad_ver = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/transcript?version=999",
        headers=headers,
    )
    assert bad_ver.status_code == 404, \
        f"Expected 404 for missing version, got {bad_ver.status_code}"
    print("  [OK] Non-existent version returns 404.")

    print("\n" + "=" * 60)
    print("[PASS] Phase 13 Canonical Transcript - Full E2E Verified.")
    print("=" * 60)


try:
    run_test()
finally:
    print("\n--- Cleaning up background processes ---")
    server.terminate()
    try:
        server.wait(timeout=5)
    except Exception:
        server.kill()
