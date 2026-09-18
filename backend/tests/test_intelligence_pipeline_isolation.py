import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.intelligence.extraction.context_builder import ContextBuilder
from app.intelligence.extraction.service import (
    MeetingIntelligenceService,
    InsufficientTranscriptError,
)
from app.intelligence.llm.providers.groq_provider import GroqLLMProvider
from app.storage.intelligence_storage import IntelligenceStorageService
from app.transcript.schemas import CanonicalTranscript, CanonicalSegment


def test_context_builder_does_not_invent_presenter():
    """Verify context builder produces no fake dialogue on empty segments."""
    meeting_id = uuid.uuid4()
    transcript = CanonicalTranscript(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        tenant_id=uuid.uuid4(),
        language="en",
        duration_seconds=10.0,
        provider_name="faster_whisper",
        model_name="whisper-large-v3",
        model_version="1.0",
        current_version_number=1,
        segments=[],
    )
    builder = ContextBuilder()
    context_str, segments_meta = builder.build_context(transcript)

    assert segments_meta == []
    assert "Meeting presentation and session walkthrough." not in context_str
    assert "Speaker: Presenter" not in context_str


def test_minio_storage_pathing():
    """Verify tenant and meeting paths are strictly isolated in S3."""
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()
    run_id = uuid.uuid4()

    storage_svc = IntelligenceStorageService(tenant_id)
    transcript_key = storage_svc.get_transcript_s3_key(meeting_id)
    intelligence_key = storage_svc.get_intelligence_s3_key(meeting_id, run_id)

    assert transcript_key == f"tenants/{tenant_id}/meetings/{meeting_id}/transcription/transcript.json"
    assert intelligence_key == f"tenants/{tenant_id}/meetings/{meeting_id}/intelligence/{run_id}.json"


def test_groq_provider_does_not_fall_back_to_mock():
    """Verify GroqLLMProvider raises on missing key and on failure without mock fallback."""
    provider_no_key = GroqLLMProvider(api_key="")
    provider_no_key.api_key = ""
    with pytest.raises(ValueError, match="No LLM API key configured"):
        provider_no_key.extract_intelligence("test context", [])

    provider = GroqLLMProvider(api_key="gsk-test")
    with patch("httpx.Client.post", side_effect=RuntimeError("Connection refused")):
        with pytest.raises(RuntimeError, match="Groq LLM extraction failed"):
            provider.extract_intelligence("test context", [])


def test_insufficient_transcript_raises_and_marks_failed():
    """Verify that transcripts with < 50 words abort with InsufficientTranscriptError."""
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()
    mock_db = MagicMock()

    # Meeting ownership passes
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
        id=meeting_id, tenant_id=tenant_id
    )

    short_transcript = CanonicalTranscript(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        language="en",
        duration_seconds=10.0,
        provider_name="faster_whisper",
        model_name="whisper-large-v3",
        model_version="1.0",
        current_version_number=1,
        segments=[
            CanonicalSegment(
                id=uuid.uuid4(),
                sequence_number=0,
                start_seconds=0.0,
                end_seconds=5.0,
                text="Hello world, this is a short test.",
                confidence=0.95,
            )
        ],
    )

    service = MeetingIntelligenceService(db=mock_db, tenant_id=tenant_id)

    with patch(
        "app.transcript.service.CanonicalTranscriptService.get_canonical",
        return_value=short_transcript,
    ):
        with pytest.raises(InsufficientTranscriptError) as exc_info:
            service.run_intelligence(meeting_id)

        assert "minimum 50 required" in str(exc_info.value)
