"""
Phase 14 – Voice Embedding Matching Engine

Design constraints
------------------
1. Candidate generation is ALWAYS scoped to the caller's tenant_id.
   There is NO global or cross-tenant voice comparison.
2. The engine returns ranked candidates above a configurable threshold.
3. The matching algorithm is cosine similarity on float-list embeddings.
   This is intentionally provider-agnostic; swap _cosine_similarity for
   a pgvector call when the vector extension is provisioned.
4. The engine returns IdentityCandidate objects; it does NOT write to the DB.
   Persistence of a chosen candidate is the responsibility of IdentityService.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import structlog

from app.speaker.schemas import IdentityCandidate

logger = structlog.get_logger(__name__)


@dataclass
class VoiceMatchConfig:
    """Tunable thresholds for the matching engine."""
    # Minimum cosine similarity to be included in candidates list
    similarity_threshold: float = 0.75
    # Maximum number of candidates to return per speaker
    max_candidates: int = 5


@dataclass
class EmbeddingProfile:
    """In-memory representation of a speaker profile with its embedding."""
    speaker_profile_id: uuid.UUID
    display_name: str
    participant_type: str
    user_id: Optional[uuid.UUID]
    embedding: List[float]


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """
    Compute cosine similarity between two float vectors.

    Returns a value in [-1.0, 1.0].  Returns 0.0 if either vector is zero-length.
    """
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class VoiceMatchingEngine:
    """
    Compares a query embedding against a set of tenant-scoped candidate profiles
    and returns ranked IdentityCandidate objects above the similarity threshold.
    """

    def __init__(self, config: Optional[VoiceMatchConfig] = None) -> None:
        self.config = config or VoiceMatchConfig()

    def find_candidates(
        self,
        query_embedding: List[float],
        tenant_profiles: List[EmbeddingProfile],
        speaker_id: uuid.UUID,
        speaker_label: str,
    ) -> List[IdentityCandidate]:
        """
        Parameters
        ----------
        query_embedding  : Embedding vector for the unknown speaker cluster.
        tenant_profiles  : All SpeakerProfiles within the caller's tenant that have
                           a non-NULL embedding.  MUST be pre-filtered by tenant_id
                           before being passed here.
        speaker_id       : The diarization Speaker.id (for logging only).
        speaker_label    : The speaker label (e.g. "SPEAKER_00") for logging.

        Returns
        -------
        Ranked list of IdentityCandidate (highest similarity first),
        limited to max_candidates above similarity_threshold.
        """
        if not query_embedding:
            logger.warning(
                "Skipping voice match: empty query embedding",
                speaker_id=str(speaker_id),
            )
            return []

        scored: List[tuple[float, IdentityCandidate]] = []

        for profile in tenant_profiles:
            if not profile.embedding:
                continue
            score = _cosine_similarity(query_embedding, profile.embedding)
            if score >= self.config.similarity_threshold:
                scored.append(
                    (
                        score,
                        IdentityCandidate(
                            speaker_profile_id=profile.speaker_profile_id,
                            display_name=profile.display_name,
                            participant_type=profile.participant_type,  # type: ignore[arg-type]
                            similarity_score=round(score, 6),
                            user_id=profile.user_id,
                        ),
                    )
                )

        # Sort by descending similarity
        scored.sort(key=lambda t: t[0], reverse=True)
        candidates = [c for _, c in scored[: self.config.max_candidates]]

        logger.info(
            "Voice match completed",
            speaker_id=str(speaker_id),
            speaker_label=speaker_label,
            profiles_evaluated=len(tenant_profiles),
            candidates_above_threshold=len(candidates),
        )
        return candidates
