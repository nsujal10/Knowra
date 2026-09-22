"""
Phase 15 – Meeting Intelligence Orchestration Service

Coordinates:
  1. Idempotency & Deduplication
  2. Transcript Retrieval (via CanonicalTranscriptService)
  3. Context Assembly (ContextBuilder)
  4. LLM Execution (LLMGateway)
  5. Evidence Validation Gate (EvidenceValidator)
  6. Persistence of structured intelligence
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy.orm import Session, selectinload

from app.intelligence.extraction.context_builder import ContextBuilder
from app.intelligence.extraction.evidence_validator import EvidenceValidator
from app.intelligence.llm.gateway import LLMGateway
from app.intelligence.models import (
    Commitment,
    Decision,
    IntelligenceRun,
    Question,
    Risk,
    Topic,
)
from app.intelligence.schemas import (
    CommitmentSchema,
    DecisionSchema,
    IntelligenceRunSchema,
    MeetingIntelligenceResponse,
    QuestionSchema,
    RiskSchema,
    TopicSchema,
)
from app.models.meeting import Meeting
from app.transcript.service import CanonicalTranscriptService, TranscriptNotFoundError

logger = structlog.get_logger(__name__)


class IntelligenceNotFoundError(Exception):
    pass


class InsufficientTranscriptError(ValueError):
    """Raised when transcript context is below the minimum required word threshold."""
    pass


class MeetingIntelligenceService:
    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def compute_idempotency_key(self, meeting_id: UUID, version_number: int) -> str:
        raw = f"{self.tenant_id}:{meeting_id}:v{version_number}:intelligence"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def run_intelligence(
        self,
        meeting_id: UUID,
        transcript_version_number: Optional[int] = None,
        force: bool = False,
    ) -> MeetingIntelligenceResponse:
        """
        Execute full meeting intelligence extraction pipeline.
        Enforces idempotency, evidence validation, and tenant isolation.
        """
        self._verify_meeting_ownership(meeting_id)

        # 1. Fetch Canonical Transcript
        t_service = CanonicalTranscriptService(db=self.db, tenant_id=self.tenant_id)
        transcript = t_service.get_canonical(
            meeting_id=meeting_id,
            version_number=transcript_version_number,
        )
        effective_version = transcript.current_version_number

        # 2. Idempotency Check
        idempotency_key = self.compute_idempotency_key(meeting_id, effective_version)
        existing_run = (
            self.db.query(IntelligenceRun)
            .filter(
                IntelligenceRun.idempotency_key == idempotency_key,
                IntelligenceRun.tenant_id == self.tenant_id,
            )
            .first()
        )
        if existing_run and existing_run.status == "COMPLETED" and not force:
            logger.info(
                "Idempotent intelligence run found, returning existing results",
                meeting_id=str(meeting_id),
                run_id=str(existing_run.id),
            )
            return self._build_response(existing_run)

        # 3. Create or Reset Run Record
        start_time = time.time()
        if existing_run:
            run = existing_run
            run.status = "PROCESSING"
            run.error_message = None
            run.processing_time_seconds = None
            # Clean up previous child records for idempotency re-run
            self.db.query(Topic).filter(Topic.intelligence_run_id == run.id).delete()
            self.db.query(Decision).filter(Decision.intelligence_run_id == run.id).delete()
            self.db.query(Risk).filter(Risk.intelligence_run_id == run.id).delete()
            self.db.query(Question).filter(Question.intelligence_run_id == run.id).delete()
            self.db.query(Commitment).filter(Commitment.intelligence_run_id == run.id).delete()
            try:
                from app.actions.models import ActionItem, ActionItemEvidence
                action_ids = [a[0] for a in self.db.query(ActionItem.id).filter(ActionItem.meeting_id == meeting_id).all()]
                if action_ids:
                    self.db.query(ActionItemEvidence).filter(ActionItemEvidence.action_item_id.in_(action_ids)).delete(synchronize_session=False)
                    self.db.query(ActionItem).filter(ActionItem.id.in_(action_ids)).delete(synchronize_session=False)
            except Exception as clean_err:
                logger.warning("Could not clean old action items", error=str(clean_err))
        else:
            run = IntelligenceRun(
                tenant_id=self.tenant_id,
                meeting_id=meeting_id,
                transcript_version_number=effective_version,
                status="PROCESSING",
                provider_name="LLMGateway",
                model_name="enterprise-intelligence",
                prompt_tokens=0,
                completion_tokens=0,
                idempotency_key=idempotency_key,
            )
            self.db.add(run)
        self.db.flush()

        # 3.5 Validate Transcript Context Length (prevent LLM hallucinations on empty text)
        total_words = sum(len(seg.text.split()) for seg in transcript.segments) if transcript.segments else 0
        if total_words < 20:
            run.status = "FAILED_NO_TRANSCRIPT"
            run.error_message = f"Transcript context too brief ({total_words} words). Minimum required: 20 words."
            self.db.commit()
            logger.warning(
                "Aborted intelligence extraction due to insufficient transcript",
                meeting_id=str(meeting_id),
                total_words=total_words,
            )
            raise InsufficientTranscriptError(
                f"Transcript has only {total_words} words; minimum 50 required for intelligence extraction."
            )

        try:
            # 4. Build Context
            builder = ContextBuilder()
            context_str, segments_meta = builder.build_context(transcript)

            # 5. Execute LLM Extraction
            gateway = LLMGateway()
            bundle = gateway.extract_all(context_str, segments_meta)

            # 6. Evidence Validation Gate (strict=False to sanitize without crashing entire batch)
            validator = EvidenceValidator(
                db=self.db,
                tenant_id=self.tenant_id,
                meeting_id=meeting_id,
            )
            validated_bundle = validator.validate_bundle(bundle, strict=False)

            # 7. Persist Topics
            for t in validated_bundle.topics:
                self.db.add(Topic(
                    tenant_id=self.tenant_id,
                    meeting_id=meeting_id,
                    intelligence_run_id=run.id,
                    title=t.title,
                    summary=t.summary,
                    start_seconds=t.start_seconds,
                    end_seconds=t.end_seconds,
                    importance_score=t.importance_score,
                    evidence_segment_ids=[str(x) for x in t.evidence_segment_ids],
                ))

            # 8. Persist Decisions
            for d in validated_bundle.decisions:
                self.db.add(Decision(
                    tenant_id=self.tenant_id,
                    meeting_id=meeting_id,
                    intelligence_run_id=run.id,
                    description=d.description,
                    rationale=d.rationale,
                    impact_level=d.impact_level,
                    decided_by_raw=d.decided_by_raw,
                    evidence_segment_ids=[str(x) for x in d.evidence_segment_ids],
                ))

            # 9. Persist Risks
            for r in validated_bundle.risks:
                self.db.add(Risk(
                    tenant_id=self.tenant_id,
                    meeting_id=meeting_id,
                    intelligence_run_id=run.id,
                    description=r.description,
                    severity=r.severity,
                    mitigation=r.mitigation,
                    status=r.status,
                    evidence_segment_ids=[str(x) for x in r.evidence_segment_ids],
                ))

            # 10. Persist Questions
            for q in validated_bundle.questions:
                self.db.add(Question(
                    tenant_id=self.tenant_id,
                    meeting_id=meeting_id,
                    intelligence_run_id=run.id,
                    question_text=q.question_text,
                    asked_by_raw=q.asked_by_raw,
                    is_answered=q.is_answered,
                    answer_text=q.answer_text,
                    evidence_segment_ids=[str(x) for x in q.evidence_segment_ids],
                ))

            # 11. Persist Commitments
            for c in validated_bundle.commitments:
                self.db.add(Commitment(
                    tenant_id=self.tenant_id,
                    meeting_id=meeting_id,
                    intelligence_run_id=run.id,
                    statement=c.statement,
                    made_by_raw=c.made_by_raw,
                    evidence_segment_ids=[str(x) for x in c.evidence_segment_ids],
                ))

            # 12. Persist Phase 16 Action Items (strictly ground-truth items only)
            action_items_to_persist = list(validated_bundle.action_items)
            if action_items_to_persist:
                from app.actions.service import ActionItemService
                action_service = ActionItemService(db=self.db, tenant_id=self.tenant_id)
                action_service.ingest_llm_action_items(
                    meeting_id=meeting_id,
                    intelligence_run_id=run.id,
                    items=action_items_to_persist,
                )

            # 12.5. Persist Immutable Intelligence JSON Artifact to MinIO
            try:
                from app.storage.intelligence_storage import IntelligenceStorageService
                intel_storage = IntelligenceStorageService(self.tenant_id)
                intel_storage.persist_intelligence_json(
                    meeting_id=meeting_id,
                    run_id=run.id,
                    payload=validated_bundle.model_dump(),
                )
            except Exception as storage_err:
                logger.warning("Could not persist intelligence JSON artifact to MinIO", error=str(storage_err))

            # 13. Finalize Run Record
            run.status = "COMPLETED"
            run.prompt_tokens = validated_bundle.prompt_tokens
            run.completion_tokens = validated_bundle.completion_tokens
            run.processing_time_seconds = round(time.time() - start_time, 3)
            self.db.commit()
            self.db.refresh(run)

            logger.info(
                "Intelligence pipeline completed successfully",
                meeting_id=str(meeting_id),
                run_id=str(run.id),
                topics_count=len(validated_bundle.topics),
                decisions_count=len(validated_bundle.decisions),
                risks_count=len(validated_bundle.risks),
            )
            return self._build_response(run)

        except Exception as exc:
            self.db.rollback()
            run.status = "FAILED"
            run.error_message = str(exc)
            self.db.add(run)
            self.db.commit()
            logger.error("Intelligence pipeline execution failed", error=str(exc))
            raise

    def get_intelligence(
        self,
        meeting_id: UUID,
        transcript_version_number: Optional[int] = None,
    ) -> MeetingIntelligenceResponse:
        """Fetch latest or specific version intelligence results."""
        self._verify_meeting_ownership(meeting_id)

        query = (
            self.db.query(IntelligenceRun)
            .filter(
                IntelligenceRun.meeting_id == meeting_id,
                IntelligenceRun.tenant_id == self.tenant_id,
                IntelligenceRun.status == "COMPLETED",
            )
        )
        if transcript_version_number is not None:
            query = query.filter(IntelligenceRun.transcript_version_number == transcript_version_number)

        run = query.order_by(IntelligenceRun.created_at.desc()).first()
        if not run:
            raise IntelligenceNotFoundError(
                f"No intelligence run found for meeting {meeting_id} in tenant {self.tenant_id}"
            )
        return self._build_response(run)

    def list_runs(self, meeting_id: UUID) -> List[IntelligenceRun]:
        """List all intelligence runs for a meeting."""
        self._verify_meeting_ownership(meeting_id)
        return (
            self.db.query(IntelligenceRun)
            .filter(
                IntelligenceRun.meeting_id == meeting_id,
                IntelligenceRun.tenant_id == self.tenant_id,
            )
            .order_by(IntelligenceRun.created_at.desc())
            .all()
        )

    def _verify_meeting_ownership(self, meeting_id: UUID) -> None:
        meeting = (
            self.db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.tenant_id == self.tenant_id)
            .first()
        )
        if not meeting:
            raise IntelligenceNotFoundError(f"Meeting {meeting_id} not found in tenant {self.tenant_id}")

    def _build_response(self, run: IntelligenceRun) -> MeetingIntelligenceResponse:
        # Load associated child entities
        topics = (
            self.db.query(Topic)
            .filter(Topic.intelligence_run_id == run.id, Topic.tenant_id == self.tenant_id)
            .order_by(Topic.importance_score.desc())
            .all()
        )
        decisions = (
            self.db.query(Decision)
            .filter(Decision.intelligence_run_id == run.id, Decision.tenant_id == self.tenant_id)
            .order_by(Decision.created_at.asc())
            .all()
        )
        risks = (
            self.db.query(Risk)
            .filter(Risk.intelligence_run_id == run.id, Risk.tenant_id == self.tenant_id)
            .order_by(Risk.created_at.asc())
            .all()
        )
        questions = (
            self.db.query(Question)
            .filter(Question.intelligence_run_id == run.id, Question.tenant_id == self.tenant_id)
            .order_by(Question.created_at.asc())
            .all()
        )
        commitments = (
            self.db.query(Commitment)
            .filter(Commitment.intelligence_run_id == run.id, Commitment.tenant_id == self.tenant_id)
            .order_by(Commitment.created_at.asc())
            .all()
        )

        return MeetingIntelligenceResponse(
            meeting_id=run.meeting_id,
            intelligence_run=IntelligenceRunSchema.model_validate(run),
            topics=[TopicSchema.model_validate(t) for t in topics],
            decisions=[DecisionSchema.model_validate(d) for d in decisions],
            risks=[RiskSchema.model_validate(r) for r in risks],
            questions=[QuestionSchema.model_validate(q) for q in questions],
            commitments=[CommitmentSchema.model_validate(c) for c in commitments],
        )
