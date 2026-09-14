"""
Phase 16 E2E Test – Action Item Extraction, Lifecycle State Machine & Candidate Workflow
=======================================================================================

Workflow tested:
----------------
1.  Register & login (Tenant A).
2.  Create a meeting and seed speakers ("David Miller", "Zira Vance") and dialogue.
3.  Create / Ingest Action Item with raw owner and relative temporal due date ("by Friday"):
    - Starts in REVIEW_REQUIRED status.
    - Resolves raw owner "David" to candidate user/speaker with confidence score.
    - Resolves "by Friday" to concrete UTC datetime.
    - Links authentic evidence segments.
4.  Deduplication & Idempotency:
    - Attempting to create / ingest the identical task resolves to the existing DB row.
    - Appends any new evidence segment without duplicating rows.
5.  Candidate vs. Truth Confirmation:
    - POST /actions/{id}/confirm promotes item from REVIEW_REQUIRED to OPEN.
    - Sets confirmed owner_id and is_confirmed = True.
    - Records ActionItemEvent audit history.
6.  Lifecycle State Machine Transitions:
    - OPEN -> IN_PROGRESS -> COMPLETED.
    - Illegal transition (e.g. REVIEW_REQUIRED -> COMPLETED) rejected with HTTP 409 Conflict.
7.  Collaboration Comments:
    - POST /actions/{id}/comments adds collaboration notes.
8.  Multi-tenant Isolation:
    - Tenant B cannot view or modify Tenant A's action items (HTTP 404).

Run from backend directory:
    python scripts/phase16_e2e_test.py
"""

import sys
import os
import time
import subprocess
from uuid import UUID, uuid4
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.actions.models import ActionItem, ActionItemEvidence, ActionItemEvent, ActionItemComment
from app.actions.service import ActionItemService

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
    print("PHASE 16 END-TO-END VERIFICATION: ACTION ITEMS & LIFECYCLE")
    print("=" * 70)

    # 1. Register & Login Tenant A
    print("\n--- 1. Register & Login (Tenant A) ---")
    test_email = f"action_{uuid4().hex[:8]}@knowra.com"
    reg = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "David Miller",
            "organization_name": f"ActionCorp_{uuid4().hex[:6]}",
        },
    )
    login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    token_a = login.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    me_a = requests.get(f"{BASE_URL}/auth/me", headers=headers_a)
    assert me_a.status_code == 200
    user_a_id = UUID(me_a.json()["user_id"])
    tenant_a_id = UUID(me_a.json()["organization_id"])
    print(f"Tenant A registered: {tenant_a_id}, User: David Miller ({user_a_id})")

    # 2. Create Meeting
    print("\n--- 2. Create Meeting ---")
    m_resp = requests.post(
        f"{BASE_URL}/meetings",
        json={"title": "Sprint 42 Action Items Planning"},
        headers=headers_a,
    )
    assert m_resp.status_code == 201, f"Create meeting failed: {m_resp.text}"
    meeting_id = UUID(m_resp.json()["id"])
    print(f"Meeting created: {meeting_id}")

    # 3. Seed Speakers & Transcript Segments
    print("\n--- 3. Seed Speakers & Transcript Segments ---")
    db = SessionLocal()
    try:
        from app.models.media_asset import MediaAsset
        from app.models.enums import MediaStatus

        media = MediaAsset(
            tenant_id=tenant_a_id,
            meeting_id=meeting_id,
            filename="sprint_planning.mp4",
            original_content_type="video/mp4",
            status=MediaStatus.READY,
            duration_seconds=40.0,
        )
        db.add(media)
        db.flush()

        spk_david = Speaker(
            tenant_id=tenant_a_id,
            meeting_id=meeting_id,
            speaker_label="SPEAKER_0",
            display_name="David Miller",
            user_id=user_a_id,
        )
        db.add(spk_david)
        db.flush()

        transcript = Transcript(
            tenant_id=tenant_a_id,
            meeting_id=meeting_id,
            media_asset_id=media.id,
            language="en",
            duration_seconds=40.0,
            provider_name="faster-whisper",
            model_name="large-v3",
            model_version="1.0",
        )
        db.add(transcript)
        db.flush()

        seg1 = TranscriptSegment(
            tenant_id=tenant_a_id,
            transcript_id=transcript.id,
            sequence_number=0,
            speaker_id=spk_david.id,
            start_seconds=10.0,
            end_seconds=15.0,
            text="David, please prepare the performance benchmarking report by Friday.",
            confidence=0.98,
        )
        seg2 = TranscriptSegment(
            tenant_id=tenant_a_id,
            transcript_id=transcript.id,
            sequence_number=1,
            speaker_id=spk_david.id,
            start_seconds=16.0,
            end_seconds=20.0,
            text="Also verify the database connection pool settings.",
            confidence=0.97,
        )
        db.add_all([seg1, seg2])
        db.commit()
        db.refresh(seg1)
        db.refresh(seg2)
        seg1_id = seg1.id
        seg2_id = seg2.id
        print(f"Seeded speaker David and 2 segments ({seg1_id}, {seg2_id})")
    finally:
        db.close()

    # 4. Ingest Action Item with Candidate Resolver & Temporal Resolver
    print("\n--- 4. Ingest Action Item (Candidate vs. Truth) ---")
    action_service = ActionItemService(db=SessionLocal(), tenant_id=tenant_a_id)
    try:
        created_item = action_service.ingest_extracted_action_item(
            meeting_id=meeting_id,
            title="Prepare performance benchmarking report",
            description="Run load tests against the Aurora PostgreSQL cluster",
            owner_raw="David",
            due_date_raw="by friday",
            priority="HIGH",
            evidence_segment_ids=[seg1_id],
        )
        print(f"Created Action Item: {created_item.id}")
        print(f"  * Status: {created_item.status} (Candidate Workflow)")
        print(f"  * Candidate User ID: {created_item.owner_candidate_user_id} (Confidence: {created_item.owner_confidence})")
        print(f"  * Resolved Due Date: {created_item.due_date}")
        print(f"  * Evidence segments: {len(created_item.evidence_items)}")

        assert created_item.status == "REVIEW_REQUIRED"
        assert created_item.owner_candidate_user_id == user_a_id
        assert created_item.due_date is not None
        assert created_item.is_confirmed is False
        action_item_id = created_item.id
    finally:
        action_service.db.close()

    # 5. Test Deduplication / Idempotency
    print("\n--- 5. Test Action Item Deduplication ---")
    db = SessionLocal()
    try:
        service_dup = ActionItemService(db=db, tenant_id=tenant_a_id)
        # Attempt to ingest the identical task with an additional evidence segment
        second_ingest = service_dup.ingest_extracted_action_item(
            meeting_id=meeting_id,
            title="prepare   performance benchmarking report  ",  # normalized match
            description="Duplicate attempt",
            owner_raw="David",
            due_date_raw="by friday",
            evidence_segment_ids=[seg2_id],
        )
        assert second_ingest.id == action_item_id, "Deduplication failed! Created duplicate row."
        
        # Verify evidence was merged without duplicating item
        ev_count = db.query(ActionItemEvidence).filter(ActionItemEvidence.action_item_id == action_item_id).count()
        assert ev_count == 2, f"Expected 2 evidence items linked, got {ev_count}"
        
        # Verify total action items in meeting is still 1
        total_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).count()
        assert total_items == 1, f"Expected 1 total item, found {total_items}"
        print(f"[PASS] Deduplication verified: Resolved to existing item {action_item_id}, merged evidence count = {ev_count}")
    finally:
        db.close()

    # 6. REST API: GET Action Item Details
    print("\n--- 6. REST: GET /actions/{action_id} ---")
    get_resp = requests.get(
        f"{BASE_URL}/actions/{action_item_id}",
        headers=headers_a,
    )
    assert get_resp.status_code == 200, f"Get action failed: {get_resp.text}"
    item_json = get_resp.json()
    assert item_json["status"] == "REVIEW_REQUIRED"
    assert len(item_json["evidence_items"]) == 2
    assert len(item_json["events"]) >= 1
    print(f"Action item retrieved via REST: {item_json['title']} [Events: {len(item_json['events'])}]")

    # 7. Candidate Confirmation (REVIEW_REQUIRED -> OPEN)
    print("\n--- 7. Confirm Candidate (REVIEW_REQUIRED -> OPEN) ---")
    confirm_resp = requests.post(
        f"{BASE_URL}/actions/{action_item_id}/confirm",
        json={"priority": "URGENT"},
        headers=headers_a,
    )
    assert confirm_resp.status_code == 200, f"Confirm failed: {confirm_resp.text}"
    confirmed_data = confirm_resp.json()
    assert confirmed_data["status"] == "OPEN"
    assert confirmed_data["is_confirmed"] is True
    assert confirmed_data["owner_id"] == str(user_a_id)
    assert confirmed_data["priority"] == "URGENT"
    print(f"[PASS] Action item confirmed: Status = {confirmed_data['status']}, Owner = {confirmed_data['owner_id']}")

    # 8. State Machine Guards & Illegal Transitions
    print("\n--- 8. State Machine Guard: Reject Illegal Transition ---")
    # Trying to jump directly from OPEN to a non-allowed state or invalid string
    illegal_resp = requests.patch(
        f"{BASE_URL}/actions/{action_item_id}/transition",
        json={"status": "REVIEW_REQUIRED"},  # cannot revert OPEN to REVIEW_REQUIRED
        headers=headers_a,
    )
    assert illegal_resp.status_code == 409, f"Expected 409 Conflict, got {illegal_resp.status_code}"
    print(f"[PASS] Illegal transition blocked: HTTP {illegal_resp.status_code}")

    # 9. Legal State Machine Lifecycle: OPEN -> IN_PROGRESS -> COMPLETED
    print("\n--- 9. Lifecycle Progress: OPEN -> IN_PROGRESS -> COMPLETED ---")
    # OPEN -> IN_PROGRESS
    prog_resp = requests.patch(
        f"{BASE_URL}/actions/{action_item_id}/transition",
        json={"status": "IN_PROGRESS", "reason": "Started benchmarking run"},
        headers=headers_a,
    )
    assert prog_resp.status_code == 200
    assert prog_resp.json()["status"] == "IN_PROGRESS"
    print("  * Status transitioned to IN_PROGRESS")

    # IN_PROGRESS -> COMPLETED
    comp_resp = requests.patch(
        f"{BASE_URL}/actions/{action_item_id}/transition",
        json={"status": "COMPLETED", "reason": "Benchmarks completed and posted"},
        headers=headers_a,
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["status"] == "COMPLETED"
    assert comp_data["completed_at"] is not None
    print(f"  * Status transitioned to COMPLETED at {comp_data['completed_at']}")

    # 10. Collaboration Comments
    print("\n--- 10. Add Collaboration Comments ---")
    comment_resp = requests.post(
        f"{BASE_URL}/actions/{action_item_id}/comments",
        json={"comment_text": "All metrics within SLA (< 120ms latency)."},
        headers=headers_a,
    )
    assert comment_resp.status_code == 201
    print(f"  * Comment added: {comment_resp.json()['comment_text']}")

    # Re-fetch item to verify audit events and comments
    full_item = requests.get(f"{BASE_URL}/actions/{action_item_id}", headers=headers_a).json()
    assert len(full_item["comments"]) == 1
    assert len(full_item["events"]) >= 4  # CREATED, CONFIRMED, STATUS(IN_PROGRESS), STATUS(COMPLETED)
    print(f"[PASS] Complete audit history captured: {len(full_item['events'])} events, {len(full_item['comments'])} comment.")

    # 11. Multi-Tenant REST Isolation Test
    print("\n--- 11. Multi-Tenant REST Isolation Test ---")
    tenant_b_email = f"action_b_{uuid4().hex[:8]}@knowra.com"
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

    forbidden_resp = requests.get(f"{BASE_URL}/actions/{action_item_id}", headers=headers_b)
    assert forbidden_resp.status_code == 404, f"Expected 404, got {forbidden_resp.status_code}"
    print(f"[PASS] Tenant B cross-tenant access blocked: HTTP {forbidden_resp.status_code}")

    print("\n" + "=" * 70)
    print("PHASE 16 VERIFICATION PASSED COMPLETELY AND SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_test()
    finally:
        server.terminate()
        server.wait()
