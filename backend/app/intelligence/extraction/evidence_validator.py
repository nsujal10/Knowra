"""
Phase 15 – Evidence Validation Gate

Guarantees that all LLM-extracted intelligence items are grounded in authentic,
canonical transcript segments belonging strictly to the authorized tenant and meeting.
Rejects hallucinated segment IDs or cross-tenant data leakage attempts.
"""

from __future__ import annotations

from typing import List, Set
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.intelligence.llm.protocol import (
    LLMActionItemOutput,
    LLMCommitmentOutput,
    LLMDecisionOutput,
    LLMIntelligenceBundle,
    LLMQuestionOutput,
    LLMRiskOutput,
    LLMTopicOutput,
)
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


class EvidenceValidationError(Exception):
    """Raised when LLM evidence fails tenant or canonical integrity validation."""
    pass


class EvidenceHallucinationError(EvidenceValidationError):
    """Raised specifically when an LLM outputs non-existent segment IDs."""
    pass


class EvidenceValidator:
    """
    Validates evidence segment IDs against the database to guarantee:
      1. Every segment exists in the canonical transcript table.
      2. Every segment strictly belongs to the caller's tenant (Tenant Isolation).
      3. Every segment strictly belongs to the target meeting.
    """

    def __init__(self, db: Session, tenant_id: UUID, meeting_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.meeting_id = meeting_id

    def get_valid_segment_ids(self) -> Set[UUID]:
        """Load all authentic segment IDs for this tenant and meeting."""
        rows = (
            self.db.query(TranscriptSegment.id)
            .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
            .filter(
                TranscriptSegment.tenant_id == self.tenant_id,
                Transcript.tenant_id == self.tenant_id,
                Transcript.meeting_id == self.meeting_id,
            )
            .all()
        )
        result_ids = set()
        for r in rows:
            if isinstance(r, (tuple, list)):
                result_ids.add(r[0])
            elif hasattr(r, "id"):
                result_ids.add(r.id)
            else:
                result_ids.add(r)
        return result_ids

    def validate_segment_ids(
        self,
        claimed_ids: List[UUID],
        item_label: str = "item",
        strict: bool = True,
    ) -> List[UUID]:
        """
        Verify that claimed_ids belong to the meeting and tenant.

        If strict=True, raises EvidenceValidationError on hallucinated or cross-tenant IDs.
        If strict=False, filters out invalid IDs and logs security warnings.
        """
        if not claimed_ids:
            return []

        valid_ids = self.get_valid_segment_ids()
        verified_ids: List[UUID] = []
        invalid_ids: List[UUID] = []

        for cid in claimed_ids:
            if cid in valid_ids:
                verified_ids.append(cid)
            else:
                invalid_ids.append(cid)

        if invalid_ids:
            msg = (
                f"Evidence validation gate failed for {item_label}: "
                f"{len(invalid_ids)} segment IDs do not belong to tenant {self.tenant_id} "
                f"or meeting {self.meeting_id}. Invalid IDs: {[str(x) for x in invalid_ids]}"
            )
            logger.warning(
                "Evidence validation failure detected",
                tenant_id=str(self.tenant_id),
                meeting_id=str(self.meeting_id),
                invalid_segment_ids=[str(x) for x in invalid_ids],
                item_label=item_label,
            )
            if strict:
                raise EvidenceHallucinationError(msg)

        return verified_ids

    def validate_bundle(
        self,
        bundle: LLMIntelligenceBundle,
        strict: bool = True,
    ) -> LLMIntelligenceBundle:
        """Filter/validate all categories in an extraction bundle."""
        # Topics
        for t in bundle.topics:
            t.evidence_segment_ids = self.validate_segment_ids(
                t.evidence_segment_ids, f"Topic '{t.title}'", strict=strict
            )

        # Decisions
        for d in bundle.decisions:
            d.evidence_segment_ids = self.validate_segment_ids(
                d.evidence_segment_ids, f"Decision '{d.description[:30]}'", strict=strict
            )

        # Risks
        for r in bundle.risks:
            r.evidence_segment_ids = self.validate_segment_ids(
                r.evidence_segment_ids, f"Risk '{r.description[:30]}'", strict=strict
            )

        # Questions
        for q in bundle.questions:
            q.evidence_segment_ids = self.validate_segment_ids(
                q.evidence_segment_ids, f"Question '{q.question_text[:30]}'", strict=strict
            )

        # Commitments
        for c in bundle.commitments:
            c.evidence_segment_ids = self.validate_segment_ids(
                c.evidence_segment_ids, f"Commitment '{c.statement[:30]}'", strict=strict
            )

        # Action Items
        for a in bundle.action_items:
            a.evidence_segment_ids = self.validate_segment_ids(
                a.evidence_segment_ids, f"Action Item '{a.title[:30]}'", strict=strict
            )

        return bundle

    def validate_action_items(
        self,
        items: List[LLMActionItemOutput],
        strict: bool = True,
    ) -> List[LLMActionItemOutput]:
        """Filter/validate evidence for a list of action item outputs."""
        for a in items:
            a.evidence_segment_ids = self.validate_segment_ids(
                a.evidence_segment_ids, f"Action Item '{a.title[:30]}'", strict=strict
            )
        return items
