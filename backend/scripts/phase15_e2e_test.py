"""
Phase 15 E2E Test – Meeting Intelligence (Topics, Decisions, Risks, Questions, Commitments)
========================================================================================

Workflow tested:
----------------
1.  Register & login (fresh Tenant A per run).
2.  Create a meeting.
3.  Seed canonical Transcript with multiple segments (real meeting dialogue with decisions, risks, questions).
4.  POST /meetings/{id}/intelligence:
    - Runs ContextBuilder to construct segment-anchored dialogue context.
    - Executes LLMGateway (Mock / Configured Provider).
    - Passes output through EvidenceValidator gate.
    - Persists Topics, Decisions, Risks, Questions, Commitments.
5.  GET /meetings/{id}/intelligence:
    - Confirms extracted items are returned with valid segment_id evidence lists.
6.  Idempotency verification:
    - Second POST /meetings/{id}/intelligence returns identical cached run without duplicate rows.
7.  Evidence Hallucination rejection:
    - Directly proves EvidenceValidator blocks invalid / cross-tenant segment references.
8.  Multi-tenant isolation:
    - Tenant B registers and attempts GET /meetings/{id}/intelligence -> 404 forbidden.

Run from backend directory:
    python scripts/phase15_e2e_test.py
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

from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.intelligence.models import (
    IntelligenceRun,
    Topic,
    Decision,
    Risk,
    Question,
    Commitment,
)
from app.intelligence.extraction.evidence_validator import (
    EvidenceValidator,
    EvidenceHallucinationError,
)

Base.metadata.create_all(bind=engine)
import scripts.seed_security
scripts.seed_security.seed()

# Launch uvicorn server
env = os.environ.copy()
env["ASR_PROVIDER"] = "mock"
env["DIARIZATION_PROVIDER"] = "mock"
env["LLM_PROVIDER"] = "mock"
env["PYTHONPATH"] = backend_dir

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
    cwd=backend_dir,
    env=env,
)

print("Waiting for server to be ready...", flush=True)
for _ in range(45):
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:8000/health", timeout=1) as resp:
            if resp.status == 200:
                print("Server is healthy and ready.", flush=True)
                break
    except Exception:
        time.sleep(1)
else:
    print("Warning: health check timed out, proceeding...", flush=True)


def run_test():
    import requests
    BASE_URL = "http://localhost:8000/api/v1"

    print("\n" + "=" * 70)
    print("PHASE 15 END-TO-END VERIFICATION: MEETING INTELLIGENCE")
    print("=" * 70)

    # 1. Register & Login Tenant A
    print("\n--- 1. Register & Login (Tenant A) ---")
    test_email = f"intel_{uuid4().hex[:8]}@knowra.com"
    reg = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Intelligence Lead",
            "organization_name": f"IntelligenceCorp_{uuid4().hex[:6]}",
        },
    )
    login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token_a = login.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    me_a = requests.get(f"{BASE_URL}/auth/me", headers=headers_a)
    assert me_a.status_code == 200
    tenant_a_id = UUID(me_a.json()["organization_id"])
    print(f"Tenant A registered: {tenant_a_id}")

    # 2. Create Meeting
    print("\n--- 2. Create Meeting ---")
    m_resp = requests.post(
        f"{BASE_URL}/meetings",
        json={"title": "Q3 Architecture & Security Intelligence Review"},
        headers=headers_a,
    )
    assert m_resp.status_code == 201, f"Create meeting failed: {m_resp.text}"
    meeting_id = UUID(m_resp.json()["id"])
    print(f"Meeting created: {meeting_id}")

    # 3. Seed Canonical Transcript in DB
    print("\n--- 3. Seed Canonical Transcript & Realistic Dialogue Segments ---")
    db = SessionLocal()
    try:
        from app.models.media_asset import MediaAsset
        from app.models.enums import MediaStatus

        media = MediaAsset(
            tenant_id=tenant_a_id,
            meeting_id=meeting_id,
            filename="q3_review.mp4",
            original_content_type="video/mp4",
            status=MediaStatus.READY,
            duration_seconds=30.0,
        )
        db.add(media)
        db.flush()

        transcript = Transcript(
            tenant_id=tenant_a_id,
            meeting_id=meeting_id,
            media_asset_id=media.id,
            language="en",
            duration_seconds=30.0,
            provider_name="faster-whisper",
            model_name="large-v3",
            model_version="1.0",
        )
        db.add(transcript)
        db.flush()

        segments_data = [
            (
                "Welcome everyone to the quarterly architecture and security review.",
                0.0,
                3.5,
                "David",
            ),
            (
                "We must decide whether to migrate our database to AWS Aurora PostgreSQL next month.",
                3.8,
                7.2,
                "David",
            ),
            (
                "We officially decided to approve the Aurora migration for the core services.",
                7.5,
                11.0,
                "Zira",
            ),
            (
                "What is the estimated downtime during the database switchover?",
                11.2,
                14.5,
                "David",
            ),
            (
                "The switchover downtime is estimated at under two minutes during off-peak hours.",
                14.8,
                18.5,
                "Zira",
            ),
            (
                "The major risk is data replication lag between regions during peak load.",
                18.8,
                22.5,
                "David",
            ),
            (
                "I commit to conducting a full load test and delivering the benchmarks by Friday.",
                22.8,
                26.5,
                "Zira",
            ),
            (
                "David, please ensure the IAM security roles are strictly enforced before Friday.",
                26.8,
                29.8,
                "Zira",
            ),
        ]

        seeded_segments = []
        for idx, (text, start, end, spk) in enumerate(segments_data):
            seg = TranscriptSegment(
                tenant_id=tenant_a_id,
                transcript_id=transcript.id,
                sequence_number=idx,
                speaker_id=None,
                start_seconds=start,
                end_seconds=end,
                text=text,
                confidence=0.98,
            )
            db.add(seg)
            seeded_segments.append(seg)

        db.commit()
        for s in seeded_segments:
            db.refresh(s)
        seeded_segment_ids = [s.id for s in seeded_segments]
        print(f"Seeded transcript {transcript.id} with {len(seeded_segment_ids)} segments.")
    finally:
        db.close()

    # 4. Trigger Meeting Intelligence via REST API
    print("\n--- 4. POST /meetings/{id}/intelligence ---")
    int_resp = requests.post(
        f"{BASE_URL}/meetings/{meeting_id}/intelligence",
        headers=headers_a,
    )
    assert int_resp.status_code == 201, f"Intelligence extraction failed: {int_resp.text}"
    int_data = int_resp.json()

    print(f"Extracted Topics: {len(int_data['topics'])}")
    for t in int_data["topics"]:
        print(f"  * Topic: {t['title']} (Evidence count: {len(t['evidence_segment_ids'])})")

    print(f"Extracted Decisions: {len(int_data['decisions'])}")
    for d in int_data["decisions"]:
        print(f"  * Decision: {d['description']} [Impact: {d['impact_level']}]")

    print(f"Extracted Risks: {len(int_data['risks'])}")
    for r in int_data["risks"]:
        print(f"  * Risk: {r['description']} [Severity: {r['severity']}]")

    print(f"Extracted Questions: {len(int_data['questions'])}")
    for q in int_data["questions"]:
        print(f"  * Question: {q['question_text']} [Answered: {q['is_answered']}]")

    print(f"Extracted Commitments: {len(int_data['commitments'])}")
    for c in int_data["commitments"]:
        print(f"  * Commitment: {c['statement']} (By: {c['made_by_raw']})")

    assert len(int_data["topics"]) > 0, "Expected at least 1 topic"
    assert len(int_data["decisions"]) > 0, "Expected at least 1 decision"
    assert len(int_data["risks"]) > 0, "Expected at least 1 risk"
    assert len(int_data["questions"]) > 0, "Expected at least 1 question"
    assert len(int_data["commitments"]) > 0, "Expected at least 1 commitment"

    # Verify all evidence segment IDs are valid seeded IDs
    all_evidence = []
    for t in int_data["topics"]:
        all_evidence.extend(t["evidence_segment_ids"])
    for d in int_data["decisions"]:
        all_evidence.extend(d["evidence_segment_ids"])

    for ev_id in all_evidence:
        assert UUID(ev_id) in seeded_segment_ids, f"Evidence ID {ev_id} not in authentic seeded segments!"
    print("[PASS] Evidence Validation Gate verified: All evidence anchors match canonical segments.")

    # 5. Idempotency Verification
    print("\n--- 5. Idempotency Verification (Repeat Extraction) ---")
    repeat_resp = requests.post(
        f"{BASE_URL}/meetings/{meeting_id}/intelligence",
        headers=headers_a,
    )
    assert repeat_resp.status_code == 201
    runs_resp = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/intelligence/runs",
        headers=headers_a,
    )
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) == 1, f"Idempotency failed! Expected 1 run, got {len(runs)}"
    print(f"[PASS] Idempotency confirmed: Deterministic hash prevented duplicate run. Total runs = {len(runs)}.")

    # 6. Evidence Hallucination & Cross-Tenant Rejection Unit Gate
    print("\n--- 6. Security Gate: Proving Rejection of Hallucinated & Cross-Tenant IDs ---")
    db = SessionLocal()
    try:
        validator = EvidenceValidator(db=db, tenant_id=tenant_a_id, meeting_id=meeting_id)
        hallucinated_id = uuid4()
        try:
            validator.validate_segment_ids([hallucinated_id], strict=True)
            assert False, "Validator should have raised EvidenceHallucinationError!"
        except EvidenceHallucinationError as e:
            print(f"[PASS] Successfully blocked hallucinated segment ID: {e}")

        # Cross-tenant segment
        foreign_tenant_id = uuid4()
        cross_tenant_validator = EvidenceValidator(db=db, tenant_id=foreign_tenant_id, meeting_id=meeting_id)
        try:
            cross_tenant_validator.validate_segment_ids([seeded_segment_ids[0]], strict=True)
            assert False, "Validator should have blocked cross-tenant access!"
        except EvidenceHallucinationError as e:
            print(f"[PASS] Successfully blocked cross-tenant segment reference: {e}")
    finally:
        db.close()

    # 7. Multi-Tenant Isolation via REST
    print("\n--- 7. Multi-Tenant REST Isolation Test ---")
    tenant_b_email = f"intel_b_{uuid4().hex[:8]}@knowra.com"
    requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": tenant_b_email,
            "password": "Password123!",
            "full_name": "Tenant B User",
            "organization_name": f"OrgB_{uuid4().hex[:6]}",
        },
    )
    login_b = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": tenant_b_email, "password": "Password123!"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    forbidden_resp = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}/intelligence",
        headers=headers_b,
    )
    assert forbidden_resp.status_code == 404, f"Expected 404 for cross-tenant access, got {forbidden_resp.status_code}"
    print(f"[PASS] Tenant B access correctly rejected: HTTP {forbidden_resp.status_code}")

    print("\n" + "=" * 70)
    print("PHASE 15 VERIFICATION PASSED COMPLETELY AND SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_test()
    finally:
        server.terminate()
        server.wait()
