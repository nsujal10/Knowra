"""
Automated End-to-End Verification Test for Live Meeting Ingestion & Multi-Track Separation

Uses FastAPI TestClient to test:
1. POST /api/v1/meetings/live/start - Initializes live meeting session & DB records
2. WebSocket /api/v1/meetings/{id}/live-stream - Ingests multi-channel audio & speaker hints
3. WebSocket /api/v1/meetings/{id}/live-transcript - Broadcasts real-time transcript & speakers
4. Validates database persistence (Meeting, Transcript, TranscriptSegment, Speaker)
5. POST /api/v1/meetings/{id}/live/end - Finalizes canonical transcript
"""

import base64
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.organization import Organization
from app.models.user import User
from app.security.tenant import TenantContext, get_tenant_context


def run_live_pipeline_test():
    print("=" * 70)
    print("  KNOWRA LIVE MULTI-TRACK INGESTION & SPEAKER IDENTIFICATION TEST")
    print("=" * 70)

    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(id=uuid.uuid4(), name="Knowra Test Org", slug=f"test-{uuid.uuid4().hex[:6]}")
            db.add(org)
            db.commit()

        user = db.query(User).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=f"tester-{uuid.uuid4().hex[:6]}@knowra.ai",
                password_hash="hashed_pw_test",
                full_name="Lead Tester",
                is_active=True,
            )
            db.add(user)
            db.commit()

        tenant_id = org.id
        user_id = user.id
    finally:
        db.close()

    # Set dependency override for tenant context
    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    client = TestClient(app)

    # Step 1: Start Live Meeting
    print("\n[Step 1] Initializing live meeting via POST /meetings/live/start...")
    start_payload = {
        "title": "Live Architecture Sync",
        "hostName": "Dr. Sarah (Host)",
    }
    res = client.post("/api/v1/meetings/live/start", json=start_payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    data = res.json()
    meeting_id = data["meetingId"]
    print(f" -> Meeting successfully created! Meeting ID: {meeting_id}")

    # Step 2: Test WebSocket Ingestion and Broadcast
    print(f"\n[Step 2] Testing multi-channel WebSocket ingestion & broadcast...")
    dummy_pcm = base64.b64encode(b"\x00" * 32000).decode("utf-8")

    # Connect subscriber websocket
    with client.websocket_connect(f"/api/v1/meetings/{meeting_id}/live-transcript") as sub_ws:
        with client.websocket_connect(f"/api/v1/meetings/{meeting_id}/live-stream") as stream_ws:
            # Channel 1: Host speaking
            payload_ch1 = {
                "channel": 1,
                "speaker_hint": "Dr. Sarah (Host)",
                "text_hint": "Welcome team to the multi-track separation test.",
                "audio_base64": dummy_pcm,
            }
            stream_ws.send_text(json.dumps(payload_ch1))

            # Channel 2: Remote participant 1
            payload_ch2_a = {
                "channel": 2,
                "speaker_hint": "Alex Connor",
                "text_hint": "Hearing you crystal clear on Channel 2 from Teams.",
                "audio_base64": dummy_pcm,
            }
            stream_ws.send_text(json.dumps(payload_ch2_a))

            # Channel 2: Remote participant 2 (distinct speaker)
            payload_ch2_b = {
                "channel": 2,
                "speaker_hint": "Elena Rostova",
                "text_hint": "Zero cross-talk detected between the three of us.",
                "audio_base64": dummy_pcm,
            }
            stream_ws.send_text(json.dumps(payload_ch2_b))

            # Read broadcasted events from subscriber
            received = []
            for _ in range(3):
                msg = sub_ws.receive_json()
                if msg.get("type") == "TRANSCRIPT_SEGMENT":
                    seg = msg["segment"]
                    received.append(seg)
                    print(f"    Broadcast Received -> [{seg['speaker']['displayName']}]: '{seg['text']}'")

    print(f"\n[Step 3] Received {len(received)} live transcript segments over WebSocket.")
    assert len(received) == 3, f"Expected 3 segments, got {len(received)}"

    # Step 4: Validate Database Persistence
    print("\n[Step 4] Validating PostgreSQL database records...")
    db = SessionLocal()
    try:
        meeting_record = db.query(Meeting).filter(Meeting.id == uuid.UUID(meeting_id)).first()
        assert meeting_record is not None, "Meeting not found in DB"
        print(f" -> Meeting record: ID={meeting_record.id}, Title='{meeting_record.title}'")

        transcript_record = db.query(Transcript).filter(Transcript.meeting_id == uuid.UUID(meeting_id)).first()
        assert transcript_record is not None, "Transcript record not found in DB"

        db_segments = db.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript_record.id
        ).order_by(TranscriptSegment.sequence_number).all()
        print(f" -> Persisted DB Segments: {len(db_segments)}")
        assert len(db_segments) >= 3, f"Expected >= 3 DB segments, found {len(db_segments)}"

        db_speakers = db.query(Speaker).filter(Speaker.meeting_id == uuid.UUID(meeting_id)).all()
        speaker_names = {s.display_name for s in db_speakers}
        print(f" -> Identified DB Speakers: {speaker_names}")
        assert "Dr. Sarah (Host)" in speaker_names, "Host speaker missing"
        assert "Alex Connor" in speaker_names or "Elena Rostova" in speaker_names, "Remote speakers missing"
    finally:
        db.close()

    # Step 5: Finalize Meeting
    print("\n[Step 5] Finalizing live meeting via POST /meetings/{id}/live/end...")
    end_res = client.post(f"/api/v1/meetings/{meeting_id}/live/end")
    assert end_res.status_code == 200, f"Expected 200, got {end_res.status_code}: {end_res.text}"
    end_data = end_res.json()
    assert end_data["status"] == "COMPLETED"
    print(f" -> Meeting finalized! Status: {end_data['status']}")

    print("\n" + "=" * 70)
    print("  ALL VERIFICATION CHECKS PASSED SUCCESSFULLY! (Method 3 Confirmed)")
    print("=" * 70)


if __name__ == "__main__":
    run_live_pipeline_test()
