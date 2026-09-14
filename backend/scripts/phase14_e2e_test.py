"""
Phase 14 E2E Test – Speaker Identification
==========================================

Workflow tested
---------------
1.  Register & login (fresh tenant per run)
2.  Create a meeting + seed a speaker cluster (diarization output, Phase 12)
3.  POST /speaker-profiles  →  create two reusable voice profiles for the tenant
4.  GET  /speaker-profiles/{id}  →  profile is retrievable and tenant-scoped
5.  GET  /meetings/{id}/speakers/{id}/candidates  →  returns candidate list (empty – no embeddings)
6.  POST /meetings/{id}/speakers/{id}/identity (action=CONFIRMED)  →  manual identity confirmation
7.  GET  /meetings/{id}/speakers/{id}/identity/history  →  history shows the CONFIRMED event
8.  POST /meetings/{id}/speakers/{id}/identity (action=REJECTED)  →  reject a second profile
9.  GET  history again  →  REJECTED event appended
10. Identity segregation guard: action=SUGGESTED from caller must be rejected with 422
11. Cross-tenant isolation:
      a. Tenant B creates a profile
      b. Tenant B tries to GET Tenant A's speaker candidates → 404 (speaker not in their tenant)
      c. Tenant A tries to confirm using Tenant B's profile_id → 404 (profile not in tenant A)

Run from the backend directory:
    python scripts/phase14_e2e_test.py
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
from app.models.speaker import Speaker

Base.metadata.create_all(bind=engine)
import scripts.seed_security
scripts.seed_security.seed()

# ── Launch server (no Celery needed – pure REST) ──────────────────────────────
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

    # ── 1. Auth & Meeting (Tenant A) ──────────────────────────────────────────
    print("\n--- 1. Register & Login (Tenant A) ---")
    email_a = f"phase14_{uuid4().hex[:8]}@knowra.com"
    requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Identity Tester",
            "organization_name": f"IdentityOrg_{uuid4().hex[:6]}",
        },
    )
    login_a = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email_a, "password": "Password123!"},
    )
    assert login_a.status_code == 200, f"Login A failed: {login_a.text}"
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    me_a = requests.get(f"{BASE_URL}/auth/me", headers=headers_a)
    tenant_id_a = UUID(me_a.json()["organization_id"])
    user_id_a = UUID(me_a.json()["user_id"])

    meeting_a = requests.post(
        f"{BASE_URL}/meetings",
        headers=headers_a,
        json={"title": "Phase 14 Identity Test Meeting"},
    )
    assert meeting_a.status_code == 201
    meeting_id_a = meeting_a.json()["id"]
    print(f"  tenant_id_a = {tenant_id_a}")
    print(f"  meeting_id_a = {meeting_id_a}")

    # ── 2. Seed Speaker cluster directly in DB ────────────────────────────────
    print("\n--- 2. Seeding Speaker cluster (diarization output) ---")
    db = SessionLocal()

    media_a = MediaAsset(
        tenant_id=tenant_id_a,
        meeting_id=UUID(meeting_id_a),
        filename="all_hands.mp4",
        original_content_type="video/mp4",
        status=MediaStatus.READY,
    )
    db.add(media_a)
    db.commit()

    # Diarization-scoped speaker cluster – no user_id linked (identity unknown)
    speaker_cluster = Speaker(
        tenant_id=tenant_id_a,
        meeting_id=UUID(meeting_id_a),
        speaker_label="SPEAKER_00",
        display_name="Speaker 1",   # generic label from diarization
        user_id=None,               # NOT linked to any user yet
    )
    db.add(speaker_cluster)
    db.commit()
    speaker_id_a = speaker_cluster.id
    print(f"  speaker_id (cluster) = {speaker_id_a}")
    db.close()

    # ── 3. Create SpeakerProfile for two known participants ───────────────────
    print("\n--- 3. POST /speaker-profiles (create two tenant-scoped profiles) ---")

    # Profile 1: an internal employee (linked user account)
    profile1_res = requests.post(
        f"{BASE_URL}/speaker-profiles",
        headers=headers_a,
        json={
            "display_name": "Alice Chen",
            "participant_type": "INTERNAL_USER",
            "user_id": str(user_id_a),
        },
    )
    assert profile1_res.status_code == 201, f"Profile1 create failed: {profile1_res.text}"
    profile1 = profile1_res.json()
    profile1_id = profile1["id"]
    print(f"  Profile 1 id={profile1_id} name={profile1['display_name']} type={profile1['participant_type']}")
    assert profile1["tenant_id"] == str(tenant_id_a)
    assert profile1["participant_type"] == "INTERNAL_USER"
    assert profile1["user_id"] == str(user_id_a)

    # Profile 2: an external participant (no user account in system)
    profile2_res = requests.post(
        f"{BASE_URL}/speaker-profiles",
        headers=headers_a,
        json={
            "display_name": "Bob Vendor (External)",
            "participant_type": "EXTERNAL_PARTICIPANT",
        },
    )
    assert profile2_res.status_code == 201, f"Profile2 create failed: {profile2_res.text}"
    profile2 = profile2_res.json()
    profile2_id = profile2["id"]
    print(f"  Profile 2 id={profile2_id} name={profile2['display_name']} type={profile2['participant_type']}")
    assert profile2["user_id"] is None

    # ── 4. GET individual profile ─────────────────────────────────────────────
    print("\n--- 4. GET /speaker-profiles/{id} ---")
    gp = requests.get(f"{BASE_URL}/speaker-profiles/{profile1_id}", headers=headers_a)
    assert gp.status_code == 200, f"Get profile failed: {gp.text}"
    assert gp.json()["display_name"] == "Alice Chen"
    print(f"  [OK] Profile retrieved: {gp.json()['display_name']}")

    # ── 5. GET candidates (no embeddings → empty list) ────────────────────────
    print("\n--- 5. GET /meetings/{id}/speakers/{id}/candidates (no embeddings -> empty) ---")
    cand_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/candidates",
        headers=headers_a,
    )
    assert cand_res.status_code == 200, f"Get candidates failed: {cand_res.text}"
    cand_data = cand_res.json()
    print(f"  candidates count = {len(cand_data['candidates'])}")
    assert cand_data["speaker_id"] == str(speaker_id_a)
    assert cand_data["speaker_label"] == "SPEAKER_00"
    assert cand_data["candidates"] == [], "Expected empty candidates (no embeddings seeded)"
    print("  [OK] Empty candidate list returned (no embeddings yet).")

    # ── 6. CONFIRM identity: manually link speaker cluster to Profile 1 ───────
    print("\n--- 6. POST /meetings/{id}/speakers/{id}/identity (action=CONFIRMED) ---")
    confirm_res = requests.post(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/identity",
        headers=headers_a,
        json={
            "speaker_profile_id": profile1_id,
            "action": "CONFIRMED",
            "note": "Voice manually confirmed by meeting host",
        },
    )
    assert confirm_res.status_code == 200, f"Confirm failed: {confirm_res.text}"
    confirm_data = confirm_res.json()
    print(f"  assignment_id={confirm_data['id']} status={confirm_data['verification_status']}")
    assert confirm_data["verification_status"] == "CONFIRMED"
    assert confirm_data["speaker_profile_id"] == profile1_id
    assert confirm_data["actioned_by_user_id"] == str(user_id_a)
    print("  [OK] Identity CONFIRMED and linked to Alice Chen.")

    # ── 7. History shows CONFIRMED event ─────────────────────────────────────
    print("\n--- 7. GET /meetings/{id}/speakers/{id}/identity/history ---")
    hist_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/identity/history",
        headers=headers_a,
    )
    assert hist_res.status_code == 200, f"Get history failed: {hist_res.text}"
    history = hist_res.json()
    events = history["history"]
    print(f"  history events: {[e['event_name'] for e in events]}")
    assert any(e["event_name"] == "SPEAKER_IDENTITY_CONFIRMED" for e in events), \
        f"Expected SPEAKER_IDENTITY_CONFIRMED in history, got: {events}"
    print("  [OK] SPEAKER_IDENTITY_CONFIRMED event found in history.")

    # ── 8. REJECT a second profile mapping ───────────────────────────────────
    print("\n--- 8. POST identity (action=REJECTED) for Profile 2 ---")
    reject_res = requests.post(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/identity",
        headers=headers_a,
        json={
            "speaker_profile_id": profile2_id,
            "action": "REJECTED",
            "note": "Definitely not Bob Vendor",
        },
    )
    assert reject_res.status_code == 200, f"Reject failed: {reject_res.text}"
    reject_data = reject_res.json()
    print(f"  status={reject_data['verification_status']} profile={reject_data['speaker_profile_id']}")
    assert reject_data["verification_status"] == "REJECTED"
    print("  [OK] Profile 2 assignment correctly REJECTED.")

    # ── 9. History now has 2 events ───────────────────────────────────────────
    print("\n--- 9. GET history (expect CONFIRMED + REJECTED events for different profiles) ---")
    hist2_res = requests.get(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/identity/history",
        headers=headers_a,
    )
    hist2 = hist2_res.json()
    print(f"  Total history events for this speaker: {len(hist2['history'])}")
    # At minimum 1 CONFIRMED event (for profile1) and 1 REJECTED event (for profile2)
    all_event_names = [e["event_name"] for e in hist2["history"]]
    print(f"  Events: {all_event_names}")
    assert "SPEAKER_IDENTITY_CONFIRMED" in all_event_names
    assert "SPEAKER_IDENTITY_REJECTED" in all_event_names
    print("  [OK] Both CONFIRMED and REJECTED events are in the history trail.")

    # ── 10. Identity segregation: action=SUGGESTED must be rejected ───────────
    print("\n--- 10. Identity segregation: caller cannot submit action=SUGGESTED ---")
    bad_res = requests.post(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/identity",
        headers=headers_a,
        json={
            "speaker_profile_id": profile1_id,
            "action": "SUGGESTED",
        },
    )
    # Either 422 (validation error) or a Pydantic rejection
    assert bad_res.status_code in (422,), \
        f"Expected 422 for action=SUGGESTED, got {bad_res.status_code}: {bad_res.text}"
    print(f"  [OK] action=SUGGESTED rejected with {bad_res.status_code}.")

    # ── 11. Tenant Isolation ──────────────────────────────────────────────────
    print("\n--- 11. Tenant Isolation ---")

    # Register Tenant B
    email_b = f"tenantb_{uuid4().hex[:8]}@knowra.com"
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

    # 11a. Tenant B cannot see Tenant A's speaker candidates
    iso_cand = requests.get(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/candidates",
        headers=headers_b,
    )
    assert iso_cand.status_code == 404, \
        f"ISOLATION FAILED: Tenant B got {iso_cand.status_code} on Tenant A speaker"
    print("  [OK] Tenant B cannot access Tenant A speaker candidates (404).")

    # 11b. Tenant B creates their OWN profile
    profile_b_res = requests.post(
        f"{BASE_URL}/speaker-profiles",
        headers=headers_b,
        json={"display_name": "Tenant B Person", "participant_type": "INTERNAL_USER"},
    )
    assert profile_b_res.status_code == 201
    profile_b_id = profile_b_res.json()["id"]
    print(f"  Tenant B profile created: {profile_b_id}")

    # 11c. Tenant A tries to confirm identity using Tenant B's profile → 404
    xpatch = requests.post(
        f"{BASE_URL}/meetings/{meeting_id_a}/speakers/{speaker_id_a}/identity",
        headers=headers_a,
        json={
            "speaker_profile_id": profile_b_id,
            "action": "CONFIRMED",
        },
    )
    assert xpatch.status_code == 404, \
        f"ISOLATION FAILED: Cross-tenant profile confirmation returned {xpatch.status_code}"
    print("  [OK] Cross-tenant profile use correctly blocked (404).")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[PASS] Phase 14 Speaker Identification - Full E2E Verified.")
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
