"""
Integration and unit tests for Action Item Deduplication, Lifecycle State Machine,
Candidate vs. Truth Workflow, and Temporal Resolution.
"""

import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock

from app.actions.models import ActionItem
from app.actions.resolver import TemporalResolver, OwnerCandidateResolver
from app.actions.service import ActionItemService, InvalidStatusTransitionError
from app.actions.schemas import ActionItemConfirmRequest
from app.models.user import User
from app.models.speaker import Speaker


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def meeting_id():
    return uuid.uuid4()


def test_deterministic_fingerprint_generation(tenant_id, meeting_id):
    title_1 = "Prepare Q3 Security Compliance Audit Report"
    title_2 = "prepare   q3   security compliance audit report"  # Different casing & whitespace

    hash_1 = ActionItemService.compute_fingerprint(tenant_id, meeting_id, title_1)
    hash_2 = ActionItemService.compute_fingerprint(tenant_id, meeting_id, title_2)

    assert hash_1 == hash_2
    assert len(hash_1) == 64


def test_temporal_expression_resolution():
    anchor = datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)  # Monday

    # "today" / "eod"
    res_today = TemporalResolver.resolve_expression("today", anchor_date=anchor)
    assert res_today is not None
    assert res_today.day == 14
    assert res_today.hour == 18

    # "tomorrow"
    res_tomorrow = TemporalResolver.resolve_expression("tomorrow", anchor_date=anchor)
    assert res_tomorrow is not None
    assert res_tomorrow.day == 15

    # "in 3 days"
    res_in_3 = TemporalResolver.resolve_expression("in 3 days", anchor_date=anchor)
    assert res_in_3 is not None
    assert res_in_3.day == 17

    # "by friday"
    res_friday = TemporalResolver.resolve_expression("by friday", anchor_date=anchor)
    assert res_friday is not None
    assert res_friday.weekday() == 4  # Friday

    # ISO string
    iso_date = "2026-10-01T15:30:00Z"
    res_iso = TemporalResolver.resolve_expression(iso_date)
    assert res_iso is not None
    assert res_iso.year == 2026
    assert res_iso.month == 10
    assert res_iso.day == 1


def test_candidate_speaker_resolution(tenant_id, meeting_id):
    mock_db = MagicMock()
    spk = MagicMock(spec=Speaker)
    spk.id = uuid.uuid4()
    spk.tenant_id = tenant_id
    spk.meeting_id = meeting_id
    spk.speaker_label = "SPEAKER_0"
    spk.display_name = "David Miller"
    spk.user_id = uuid.uuid4()

    mock_db.query.return_value.filter.return_value.all.return_value = [spk]

    resolver = OwnerCandidateResolver(db=mock_db, tenant_id=tenant_id)

    # Match by label
    cand_user, cand_spk, conf = resolver.resolve_candidate("SPEAKER_0", meeting_id)
    assert cand_user == spk.user_id
    assert cand_spk == spk.id
    assert conf >= 0.90

    # Match by display name
    cand_user2, cand_spk2, conf2 = resolver.resolve_candidate("David", meeting_id)
    assert cand_user2 == spk.user_id
    assert cand_spk2 == spk.id


def test_action_item_state_machine_transitions(tenant_id, meeting_id):
    mock_db = MagicMock()
    service = ActionItemService(db=mock_db, tenant_id=tenant_id)

    item = ActionItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        title="Test Action Item",
        status="REVIEW_REQUIRED",
        fingerprint_hash="abc",
        is_confirmed=False,
    )

    service.get_action_item = MagicMock(return_value=item)

    # Transitioning directly from REVIEW_REQUIRED to IN_PROGRESS is forbidden
    with pytest.raises(InvalidStatusTransitionError):
        service.transition_status(item.id, "IN_PROGRESS")

    # Transitioning directly from REVIEW_REQUIRED to COMPLETED is forbidden
    with pytest.raises(InvalidStatusTransitionError):
        service.transition_status(item.id, "COMPLETED")

    # Legal: confirm promotes REVIEW_REQUIRED to OPEN
    item.owner_candidate_user_id = uuid.uuid4()
    confirmed_item = service.confirm_action_item(item.id)
    assert confirmed_item.status == "OPEN"
    assert confirmed_item.is_confirmed is True

    # Legal: OPEN -> IN_PROGRESS
    service.transition_status(item.id, "IN_PROGRESS")
    assert item.status == "IN_PROGRESS"

    # Legal: IN_PROGRESS -> COMPLETED
    service.transition_status(item.id, "COMPLETED")
    assert item.status == "COMPLETED"
    assert item.completed_at is not None


def test_deduplication_returns_existing_item(tenant_id, meeting_id):
    mock_db = MagicMock()
    service = ActionItemService(db=mock_db, tenant_id=tenant_id)

    existing_item = ActionItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        title="Configure CORS settings",
        fingerprint_hash=ActionItemService.compute_fingerprint(tenant_id, meeting_id, "Configure CORS settings"),
        status="REVIEW_REQUIRED",
        evidence_items=[],
    )

    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = existing_item

    # Ingesting the exact same task
    retrieved = service.ingest_extracted_action_item(
        meeting_id=meeting_id,
        title="Configure CORS settings",
        owner_raw="David",
    )

    assert retrieved.id == existing_item.id
    # Ensure no new action item was added
    mock_db.add.assert_not_called()
