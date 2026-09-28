"""
End-to-End Verification Test for Hinglish (Code-Mixed) Live & Batch Transcription Pipeline

Validates:
1. Groq Whisper provider initialization with whisper-large-v3
2. Priming prompt resolution for 'hinglish', 'hi', and 'en'
3. Live session initialization with language='hinglish'
4. Audio chunk & text-hint ingestion of bilingual code-mixed technical dialogue
5. Verification that transcripts are persisted in PostgreSQL without forced Devanagari conversion
"""

import base64
import os
import sys
import uuid
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.organization import Organization
from app.models.user import User
from app.ai.transcription.factory import get_transcription_provider
from app.services.live_meeting_service import LiveMeetingManager


def run_hinglish_verification():
    print("=" * 75)
    print("  KNOWRA HINGLISH (CODE-MIXED) TRANSCRIPTION PIPELINE TEST")
    print("=" * 75)

    # 1. Verify Provider & Prompts
    print("\n[Step 1] Verifying Groq Whisper Provider configuration...")
    provider = get_transcription_provider()
    print(f" -> Provider: {type(provider).__name__}")
    print(f" -> Model: {provider.model}")
    assert provider.model == "whisper-large-v3", f"Expected whisper-large-v3, got {provider.model}"

    # Verify language normalization & prompt resolution
    iso_hinglish = provider._normalize_language("hinglish")
    prompt_hinglish = provider._get_priming_prompt("hinglish")
    assert iso_hinglish is None, f"Expected None for Hinglish ISO to avoid forcing Devanagari, got {iso_hinglish}"
    assert "sprint planning" in prompt_hinglish, "Expected Hinglish conversational priming prompt"
    print(" -> Language normalization for Hinglish verified: ISO=None (prevents Devanagari constraint)")
    print(f" -> Prompt conditioning verified (length: {len(prompt_hinglish)} characters)")

    # 2. Database & Tenant Setup
    print("\n[Step 2] Setting up test tenant and user in database...")
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(id=uuid.uuid4(), name="Knowra Hinglish Org", slug=f"test-hinglish-{uuid.uuid4().hex[:6]}")
            db.add(org)
            db.commit()

        user = db.query(User).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=f"tester-hinglish-{uuid.uuid4().hex[:6]}@knowra.ai",
                password_hash="hashed_pw_test",
                full_name="Sujal Nage",
                is_active=True,
            )
            db.add(user)
            db.commit()

        tenant_id = org.id
        user_id = user.id

        # 3. Live Meeting Session with Hinglish
        print("\n[Step 3] Initializing LiveMeetingManager session with language='hinglish'...")
        meeting_id = uuid.uuid4()
        manager = LiveMeetingManager.get_instance()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        session = loop.run_until_complete(
            manager.start_session(
                db=db,
                meeting_id=meeting_id,
                tenant_id=tenant_id,
                owner_id=user_id,
                host_name="Sujal Nage",
                remote_name="Rahul Sharma, Priya Verma",
                language="hinglish",
            )
        )
        assert session is not None
        assert session.language == "hinglish"
        print(f" -> Live session started successfully! Meeting ID: {meeting_id}, Language: {session.language}")

        # 4. Ingest Code-Mixed Technical Dialogue
        print("\n[Step 4] Ingesting multi-channel Hinglish dialogue...")
        hinglish_turns = [
            (1, "Sujal Nage", "Team, aaj hum architecture aur sprint deployment pipeline discuss karenge."),
            (2, "Rahul Sharma", "Haan Sujal, maine database migration aur redis cache index optimize kar diya hai. Latency 60% reduce ho gayi hai."),
            (2, "Priya Verma", "Awesome Rahul! Kya hum Friday tak live transcription feature production release me merge kar sakte hain?"),
            (1, "Sujal Nage", "Definitely, Thursday ko final regression testing hogi aur Friday 3 PM deploy karenge."),
        ]

        dummy_pcm = b"\x00" * 32000

        for ch, spk, txt in hinglish_turns:
            loop.run_until_complete(
                manager.ingest_audio_chunk(
                    meeting_id=meeting_id,
                    channel_id=ch,
                    audio_bytes=dummy_pcm,
                    speaker_hint=spk,
                    text_hint=txt,
                )
            )
            print(f"    [Ch {ch}] {spk}: {txt}")

        # 5. Verify DB Persistence
        print("\n[Step 5] Validating persisted transcript segments in PostgreSQL...")
        segments = (
            db.query(TranscriptSegment)
            .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(TranscriptSegment.sequence_number.asc())
            .all()
        )
        assert len(segments) == len(hinglish_turns), f"Expected {len(hinglish_turns)} segments, found {len(segments)}"

        transcript_row = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
        assert transcript_row.language == "hinglish", f"Expected transcript language 'hinglish', got '{transcript_row.language}'"

        print(f" -> Persisted {len(segments)} segments with language='{transcript_row.language}'!")
        for idx, s in enumerate(segments):
            assert "architecture" in s.text or "migration" in s.text or "transcription" in s.text or "testing" in s.text
            print(f"    Seg {idx + 1}: {s.text}")

        # 6. Finalize session
        loop.run_until_complete(manager.end_session(meeting_id))
        print("\n[Step 6] Session ended and cleaned up.")

        print("\n" + "=" * 75)
        print("  ALL HINGLISH END-TO-END PIPELINE CHECKS PASSED (100% SUCCESS)!")
        print("=" * 75)

    finally:
        db.close()


if __name__ == "__main__":
    run_hinglish_verification()
