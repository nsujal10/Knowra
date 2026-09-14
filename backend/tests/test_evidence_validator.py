"""
Unit tests for Evidence Validation Gate.
Proves that the pipeline rejects LLM output if it hallucinates a segment_id
or attempts cross-tenant referencing.
"""

import uuid
import pytest
from unittest.mock import MagicMock

from app.intelligence.extraction.evidence_validator import (
    EvidenceValidator,
    EvidenceHallucinationError,
)
from app.intelligence.llm.protocol import (
    LLMTopicOutput,
    LLMDecisionOutput,
    LLMActionItemOutput,
    LLMIntelligenceBundle,
)
from app.models.transcript_segment import TranscriptSegment


@pytest.fixture
def tenant_a():
    return uuid.uuid4()


@pytest.fixture
def tenant_b():
    return uuid.uuid4()


@pytest.fixture
def meeting_id():
    return uuid.uuid4()


@pytest.fixture
def mock_db():
    return MagicMock()


def test_valid_evidence_passes(tenant_a, meeting_id, mock_db):
    seg1 = uuid.uuid4()
    seg2 = uuid.uuid4()

    mock_db_seg1 = MagicMock(spec=TranscriptSegment)
    mock_db_seg1.id = seg1
    mock_db_seg1.tenant_id = tenant_a
    mock_db_seg1.text = "We agreed to deploy the new microservice by Friday."

    mock_db_seg2 = MagicMock(spec=TranscriptSegment)
    mock_db_seg2.id = seg2
    mock_db_seg2.tenant_id = tenant_a
    mock_db_seg2.text = "Sarah will lead the security review."

    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_db_seg1, mock_db_seg2]

    validator = EvidenceValidator(db=mock_db, tenant_id=tenant_a, meeting_id=meeting_id)

    # Valid segment passes
    valid_ids = validator.validate_segment_ids([seg1, seg2], strict=True)
    assert set(valid_ids) == {seg1, seg2}


def test_hallucinated_segment_id_rejected(tenant_a, meeting_id, mock_db):
    seg_real = uuid.uuid4()
    seg_fake = uuid.uuid4()

    mock_db_seg = MagicMock(spec=TranscriptSegment)
    mock_db_seg.id = seg_real
    mock_db_seg.tenant_id = tenant_a
    mock_db_seg.text = "Valid text"

    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_db_seg]

    validator = EvidenceValidator(db=mock_db, tenant_id=tenant_a, meeting_id=meeting_id)

    # Strict mode must raise EvidenceHallucinationError
    with pytest.raises(EvidenceHallucinationError) as exc_info:
        validator.validate_segment_ids([seg_real, seg_fake], strict=True)

    assert str(seg_fake) in str(exc_info.value)

    # Non-strict mode strips the hallucinated ID
    sanitized = validator.validate_segment_ids([seg_real, seg_fake], strict=False)
    assert sanitized == [seg_real]


def test_cross_tenant_evidence_rejected(tenant_a, tenant_b, meeting_id, mock_db):
    """
    If an LLM returns a segment ID belonging to another tenant, the query filter
    `Transcript.tenant_id == self.tenant_id` excludes it from valid segments.
    The validator must reject it.
    """
    foreign_tenant_seg = uuid.uuid4()

    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.filter.return_value = query_mock
    # Cross tenant segment is not found under tenant_a
    query_mock.all.return_value = []

    validator = EvidenceValidator(db=mock_db, tenant_id=tenant_a, meeting_id=meeting_id)

    with pytest.raises(EvidenceHallucinationError) as exc_info:
        validator.validate_segment_ids([foreign_tenant_seg], strict=True)

    assert "Evidence validation gate failed" in str(exc_info.value)


def test_bundle_validation_sanitizes_hallucinations(tenant_a, meeting_id, mock_db):
    valid_id = uuid.uuid4()
    fake_id = uuid.uuid4()

    mock_seg = MagicMock(spec=TranscriptSegment)
    mock_seg.id = valid_id
    mock_seg.tenant_id = tenant_a
    mock_seg.text = "Architecture planning session"

    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_seg]

    validator = EvidenceValidator(db=mock_db, tenant_id=tenant_a, meeting_id=meeting_id)

    raw_bundle = LLMIntelligenceBundle(
        topics=[
            LLMTopicOutput(
                title="Arch Review",
                summary="Discussing microservices",
                evidence_segment_ids=[valid_id, fake_id],
            )
        ],
        action_items=[
            LLMActionItemOutput(
                title="Deploy service",
                evidence_segment_ids=[fake_id],
            )
        ],
    )

    sanitized = validator.validate_bundle(raw_bundle, strict=False)
    # The topic should keep only the valid segment
    assert sanitized.topics[0].evidence_segment_ids == [valid_id]
    # The action item had only fake_id, so it should be empty list
    assert sanitized.action_items[0].evidence_segment_ids == []
