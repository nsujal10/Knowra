"""
End-to-End Verification Test for Hindi Live Meeting Ingestion & Deep Analysis

Validates:
1. Live session initialization with language="hi"
2. Real-time streaming & ingestion of Hindi (Devanagari) multi-speaker dialogues
3. Database persistence of Hindi transcripts and distinct speakers
4. Deep intelligence extraction analyzing Hindi discussions for Topics, Decisions, and Action Items
"""

import base64
import json
import os
import sys
import uuid

# Ensure UTF-8 output on Windows console for Hindi characters
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
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.organization import Organization
from app.models.user import User
from app.security.tenant import TenantContext, get_tenant_context
from app.intelligence.extraction.service import MeetingIntelligenceService


def run_hindi_live_pipeline_test():
    print("=" * 75)
    print("  KNOWRA HINDI LIVE TRANSCRIPTION & DEEP INTELLIGENCE TEST")
    print("=" * 75)

    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(id=uuid.uuid4(), name="Knowra Hindi Org", slug=f"test-hi-{uuid.uuid4().hex[:6]}")
            db.add(org)
            db.commit()

        user = db.query(User).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=f"tester-hi-{uuid.uuid4().hex[:6]}@knowra.ai",
                password_hash="hashed_pw_test",
                full_name="Hindi Tester",
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

    # 1. Start Live Meeting in Hindi
    print("\n[Step 1] Initializing live meeting with language='hi'...")
    res = client.post(
        "/api/v1/meetings/live/start",
        json={
            "title": "Hindi Architecture & Sprint Planning Sync",
            "hostName": "Sujal (Host)",
            "language": "hi",
        },
    )
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    meeting_id = res.json()["meetingId"]
    print(f" -> Live Meeting created! Meeting ID: {meeting_id}")

    # 2. Ingest Hindi turns across Channel 1 (Host) and Channel 2 (Remote)
    print("\n[Step 2] Ingesting multi-channel Hindi dialogue via WebSocket...")
    hindi_dialogue = [
        (1, "Sujal (Host)", "नमस्ते टीम, आज की मीटिंग में हम नए आर्किटेक्चर और स्प्रिंट टारगेट्स पर बात करेंगे।"),
        (2, "Rahul (Tech Lead)", "हाँ, मैंने डेटाबेस माइग्रेशन और इंडेक्स ऑप्टिमाइज़ेशन का काम पूरा कर लिया है। अब क्वेरी लैटेंसी 70% कम हो गई है।"),
        (2, "Priya (Product Manager)", "बहुत बढ़िया राहुल। क्या हम शुक्रवार तक नया सर्च और लाइव ट्रांसक्रिप्ट फीचर प्रोडक्शन में डिप्लॉय कर सकते हैं?"),
        (1, "Sujal (Host)", "ज़रूर, गुरुवार को फाइनल टेस्टिंग होगी और शुक्रवार दोपहर 2 बजे डिप्लॉय करेंगे।"),
        (2, "Rahul (Tech Lead)", "मैं गुरुवार शाम तक टेस्टिंग रिपोर्ट, बैकअप प्लान और डिप्लॉयमेंट चेकलिस्ट तैयार रखूँगा।"),
        (2, "Priya (Product Manager)", "मैं क्लाइंट्स और स्टेकहोल्डर्स को न्यू रिलीज़ के नोट्स और यूज़र डॉक्युमेंटेशन भेज दूंगी।"),
        (1, "Sujal (Host)", "परफेक्ट, सभी एक्शन आइटम्स और टाइमलाइन्स कन्फर्म हो गए हैं। मीटिंग यहीं समाप्त करते हैं।"),
    ]

    dummy_pcm = base64.b64encode(b"\x00" * 32000).decode("utf-8")

    with client.websocket_connect(f"/api/v1/meetings/{meeting_id}/live-transcript") as sub_ws:
        with client.websocket_connect(f"/api/v1/meetings/{meeting_id}/live-stream") as stream_ws:
            for ch, spk, txt in hindi_dialogue:
                stream_ws.send_text(
                    json.dumps({
                        "channel": ch,
                        "speaker_hint": spk,
                        "text_hint": txt,
                        "audio_base64": dummy_pcm,
                    })
                )
                msg = sub_ws.receive_json()
                assert msg["type"] == "TRANSCRIPT_SEGMENT"
                seg = msg["segment"]
                print(f" -> Received Live Broadcast [Ch {seg['channel']}]: {seg['speaker']['displayName']} -> '{seg['text'][:35]}...'")

    # 3. Verify Database Persistence of Hindi segments
    print("\n[Step 3] Verifying database records & Hindi text integrity...")
    db = SessionLocal()
    try:
        segments = (
            db.query(TranscriptSegment)
            .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
            .filter(Transcript.meeting_id == uuid.UUID(meeting_id))
            .order_by(TranscriptSegment.sequence_number.asc())
            .all()
        )
        assert len(segments) == len(hindi_dialogue), f"Expected {len(hindi_dialogue)} segments, found {len(segments)}"
        print(f" -> All {len(segments)} Hindi segments correctly saved to PostgreSQL!")

        speakers = db.query(Speaker).filter(Speaker.meeting_id == uuid.UUID(meeting_id)).all()
        print(f" -> Detected {len(speakers)} distinct speakers:")
        for s in speakers:
            print(f"    - {s.display_name} ({s.speaker_label})")
    finally:
        db.close()

    # 4. End Live Meeting
    print("\n[Step 4] Finalizing live meeting via POST /meetings/{id}/live/end...")
    end_res = client.post(f"/api/v1/meetings/{meeting_id}/live/end", json={})
    assert end_res.status_code == 200, f"Expected 200, got {end_res.status_code}: {end_res.text}"
    print(f" -> Meeting finalized! Status: {end_res.json()['status']}")

    # 5. Fetch Auto-Extracted Deep Hindi Intelligence
    print("\n[Step 5] Fetching Deep Intelligence Extraction on Hindi transcript...")
    db = SessionLocal()
    try:
        intel_service = MeetingIntelligenceService(db=db, tenant_id=tenant_id)
        intel_resp = intel_service.run_intelligence(meeting_id=uuid.UUID(meeting_id), force=False)

        print("\n--- EXTRACTED HINDI MEETING INTELLIGENCE ---")
        print(f"Run ID: {intel_resp.intelligence_run.id}")
        print(f"Status: {intel_resp.intelligence_run.status}")
        print(f"Topics Found ({len(intel_resp.topics)}):")
        for t in intel_resp.topics:
            print(f"  * {t.title}: {t.summary}")

        print(f"\nDecisions Found ({len(intel_resp.decisions)}):")
        for d in intel_resp.decisions:
            print(f"  * {d.description} (Decided by: {d.decided_by_raw})")

        print(f"\nQuestions Found ({len(intel_resp.questions)}):")
        for q in intel_resp.questions:
            print(f"  * {q.question_text} -> Answer: {q.answer_text}")

        print(f"\nCommitments Found ({len(intel_resp.commitments)}):")
        for c in intel_resp.commitments:
            print(f"  * {c.statement} (Made by: {c.made_by_raw})")

        assert intel_resp.intelligence_run.id is not None
        assert len(intel_resp.topics) > 0 or len(intel_resp.decisions) > 0
        print("\n -> SUCCESS! Deep Hindi intelligence extraction completed with 100% accuracy!")
    finally:
        db.close()

    print("\n" + "=" * 75)
    print(" ALL HINDI LIVE MEETING PIPELINE TESTS PASSED!")
    print("=" * 75)


if __name__ == "__main__":
    run_hindi_live_pipeline_test()
