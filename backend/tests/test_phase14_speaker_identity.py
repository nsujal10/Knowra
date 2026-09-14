from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, call

import pytest
from pydantic import ValidationError

from app.speaker.matching import (
    EmbeddingProfile,
    VoiceMatchConfig,
    VoiceMatchingEngine,
    _cosine_similarity,
)
from app.speaker.schemas import (
    IdentityCandidate,
    IdentityConfirmRequest,
    SpeakerProfileCreateRequest,
    SpeakerProfileResponse,
)

from app.speaker.matching import (
    EmbeddingProfile,
    VoiceMatchConfig,
    VoiceMatchingEngine,
    _cosine_similarity,
)
from app.speaker.schemas import (
    IdentityCandidate,
    IdentityConfirmRequest,
    SpeakerProfileCreateRequest,
    SpeakerProfileResponse,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = uuid.uuid4()
OTHER_TENANT_ID = uuid.uuid4()
MEETING_ID = uuid.uuid4()
SPEAKER_ID = uuid.uuid4()
PROFILE_ID = uuid.uuid4()


def _make_profile(
    tenant_id: uuid.UUID = TENANT_ID,
    embedding: List[float] | None = None,
    participant_type: str = "INTERNAL_USER",
) -> EmbeddingProfile:
    # Use sentinel to distinguish "not provided" from "explicitly empty list"
    actual_embedding = [1.0, 0.0, 0.0] if embedding is None else embedding
    return EmbeddingProfile(
        speaker_profile_id=uuid.uuid4(),
        display_name="Alice",
        participant_type=participant_type,
        user_id=None,
        embedding=actual_embedding,
    )


# ---------------------------------------------------------------------------
# Cosine similarity unit tests
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.5, 0.25]
        assert _cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-9)

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=1e-9)

    def test_opposite_vectors(self):
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0, abs=1e-9)

    def test_zero_vector_returns_zero(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_mismatched_length_returns_zero(self):
        assert _cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.5]) == 0.0

    def test_partial_similarity(self):
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        expected = 1.0 / math.sqrt(2.0)
        assert _cosine_similarity(a, b) == pytest.approx(expected, abs=1e-6)


# ---------------------------------------------------------------------------
# VoiceMatchingEngine tests
# ---------------------------------------------------------------------------

class TestVoiceMatchingEngine:
    def setup_method(self):
        self.config = VoiceMatchConfig(similarity_threshold=0.8, max_candidates=3)
        self.engine = VoiceMatchingEngine(self.config)

    def test_exact_match_returned(self):
        query = [1.0, 0.0, 0.0]
        profiles = [_make_profile(embedding=[1.0, 0.0, 0.0])]
        results = self.engine.find_candidates(query, profiles, SPEAKER_ID, "SPEAKER_00")
        assert len(results) == 1
        assert results[0].similarity_score == pytest.approx(1.0, abs=1e-6)

    def test_below_threshold_excluded(self):
        query = [1.0, 0.0, 0.0]
        # Orthogonal → similarity = 0 (below 0.8 threshold)
        profiles = [_make_profile(embedding=[0.0, 1.0, 0.0])]
        results = self.engine.find_candidates(query, profiles, SPEAKER_ID, "SPEAKER_00")
        assert len(results) == 0

    def test_ranking_descending(self):
        query = [1.0, 0.5, 0.0]
        p1 = _make_profile(embedding=[1.0, 0.0, 0.0])  # partial match
        p2 = _make_profile(embedding=[1.0, 0.5, 0.0])  # exact match
        profiles = [p1, p2]
        results = self.engine.find_candidates(query, profiles, SPEAKER_ID, "SPEAKER_00")
        # Both should pass threshold if > 0.8; exact match must be first
        assert results[0].similarity_score >= results[-1].similarity_score

    def test_max_candidates_respected(self):
        query = [1.0, 0.0, 0.0]
        profiles = [_make_profile(embedding=[1.0, 0.0, 0.0]) for _ in range(10)]
        results = self.engine.find_candidates(query, profiles, SPEAKER_ID, "SPEAKER_00")
        assert len(results) <= self.config.max_candidates

    def test_empty_query_embedding_returns_empty(self):
        profiles = [_make_profile(embedding=[1.0, 0.0, 0.0])]
        results = self.engine.find_candidates([], profiles, SPEAKER_ID, "SPEAKER_00")
        assert results == []

    def test_profiles_without_embeddings_skipped(self):
        query = [1.0, 0.0, 0.0]
        # A profile whose embedding list is genuinely empty → _cosine_similarity → 0 due
        # to zero-magnitude vector guard, but the explicit `if not profile.embedding`
        # short-circuits first.
        p = _make_profile(embedding=[])
        results = self.engine.find_candidates(query, [p], SPEAKER_ID, "SPEAKER_00")
        # Empty embedding → skipped → no candidates
        assert results == []

    def test_similarity_score_clamped_to_six_decimals(self):
        query = [1.0, 0.0, 0.0]
        profiles = [_make_profile(embedding=[1.0, 0.0, 0.0])]
        results = self.engine.find_candidates(query, profiles, SPEAKER_ID, "SPEAKER_00")
        # round(1.0, 6) == 1.0
        assert results[0].similarity_score == 1.0

    def test_candidate_contains_correct_profile_id(self):
        query = [1.0, 0.0, 0.0]
        profile = _make_profile(embedding=[1.0, 0.0, 0.0])
        results = self.engine.find_candidates(query, [profile], SPEAKER_ID, "SPEAKER_00")
        assert results[0].speaker_profile_id == profile.speaker_profile_id


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSpeakerIdentitySchemas:
    def test_create_request_valid(self):
        req = SpeakerProfileCreateRequest(
            display_name="Bob Smith",
            participant_type="INTERNAL_USER",
            user_id=uuid.uuid4(),
        )
        assert req.display_name == "Bob Smith"

    def test_create_request_empty_name_raises(self):
        with pytest.raises(ValidationError):
            SpeakerProfileCreateRequest(display_name="", participant_type="UNKNOWN")

    def test_confirm_request_valid_confirmed(self):
        req = IdentityConfirmRequest(
            speaker_profile_id=uuid.uuid4(),
            action="CONFIRMED",
        )
        assert req.action == "CONFIRMED"

    def test_confirm_request_valid_rejected(self):
        req = IdentityConfirmRequest(
            speaker_profile_id=uuid.uuid4(),
            action="REJECTED",
        )
        assert req.action == "REJECTED"

    def test_confirm_request_suggested_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            IdentityConfirmRequest(
                speaker_profile_id=uuid.uuid4(),
                action="SUGGESTED",
            )

    def test_identity_candidate_similarity_bounds(self):
        with pytest.raises(ValidationError):
            IdentityCandidate(
                speaker_profile_id=uuid.uuid4(),
                display_name="X",
                participant_type="UNKNOWN",
                similarity_score=1.5,  # invalid
            )

    def test_identity_candidate_min_similarity(self):
        with pytest.raises(ValidationError):
            IdentityCandidate(
                speaker_profile_id=uuid.uuid4(),
                display_name="X",
                participant_type="UNKNOWN",
                similarity_score=-0.1,  # invalid
            )


# ---------------------------------------------------------------------------
# Service unit tests (DB mocked)
# ---------------------------------------------------------------------------

class TestSpeakerIdentityService:
    def _make_mock_speaker(self) -> MagicMock:
        s = MagicMock()
        s.id = SPEAKER_ID
        s.meeting_id = MEETING_ID
        s.tenant_id = TENANT_ID
        s.speaker_label = "SPEAKER_00"
        return s

    def _make_mock_db(self, speaker: MagicMock = None) -> MagicMock:
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        if speaker:
            mock_query.first.return_value = speaker
        else:
            mock_query.first.return_value = None
        mock_query.all.return_value = []
        return mock_db

    def test_get_candidates_empty_profiles_returns_empty(self):
        from app.speaker.service import SpeakerIdentityService

        speaker = self._make_mock_speaker()
        mock_db = self._make_mock_db(speaker)
        # all() returns empty list of profiles
        mock_db.query.return_value.filter.return_value.all.return_value = []

        service = SpeakerIdentityService(db=mock_db, tenant_id=TENANT_ID)
        result = service.get_identity_candidates(
            meeting_id=MEETING_ID,
            speaker_id=SPEAKER_ID,
        )
        assert result.candidates == []
        assert result.speaker_id == SPEAKER_ID

    def test_get_candidates_speaker_not_found_raises(self):
        from app.speaker.service import SpeakerIdentityService, IdentityNotFoundError

        mock_db = self._make_mock_db(speaker=None)
        service = SpeakerIdentityService(db=mock_db, tenant_id=TENANT_ID)
        with pytest.raises(IdentityNotFoundError):
            service.get_identity_candidates(
                meeting_id=MEETING_ID,
                speaker_id=SPEAKER_ID,
            )

    def test_confirm_identity_invalid_action_raises(self):
        from app.speaker.service import SpeakerIdentityService, IdentityViolationError

        speaker = self._make_mock_speaker()
        mock_db = self._make_mock_db(speaker)

        service = SpeakerIdentityService(db=mock_db, tenant_id=TENANT_ID)
        with pytest.raises(IdentityViolationError, match="CONFIRMED or REJECTED"):
            service.confirm_identity(
                meeting_id=MEETING_ID,
                speaker_id=SPEAKER_ID,
                speaker_profile_id=PROFILE_ID,
                action="SUGGESTED",  # invalid
                actor_user_id=uuid.uuid4(),
            )

    def test_create_profile_commits_and_returns(self):
        from app.speaker.service import SpeakerIdentityService

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        # Simulate refresh populating the object
        profile_mock = MagicMock()
        profile_mock.id = PROFILE_ID
        profile_mock.tenant_id = TENANT_ID
        profile_mock.user_id = None
        profile_mock.display_name = "Bob"
        profile_mock.participant_type = "EXTERNAL_PARTICIPANT"
        profile_mock.embedding_model = None
        profile_mock.created_at = datetime.now(timezone.utc)
        profile_mock.updated_at = datetime.now(timezone.utc)

        def _refresh(obj):
            obj.id = PROFILE_ID
            obj.tenant_id = TENANT_ID
            obj.user_id = None
            obj.display_name = "Bob"
            obj.participant_type = "EXTERNAL_PARTICIPANT"
            obj.embedding_model = None
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh.side_effect = _refresh

        service = SpeakerIdentityService(db=mock_db, tenant_id=TENANT_ID)
        req = SpeakerProfileCreateRequest(
            display_name="Bob",
            participant_type="EXTERNAL_PARTICIPANT",
        )
        result = service.create_profile(req)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.display_name == "Bob"
