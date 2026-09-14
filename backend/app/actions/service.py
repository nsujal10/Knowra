import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.actions.models import ActionItem, ActionItemEvidence, ActionItemEvent, ActionItemComment
from app.actions.resolver import TemporalResolver, OwnerCandidateResolver
from app.actions.schemas import ActionItemConfirmRequest, ActionItemUpdate
from app.models.user import User


class InvalidStatusTransitionError(ValueError):
    """Raised when an illegal action item state transition is attempted."""
    pass


class ActionItemService:
    """
    Enterprise lifecycle service for Action Items.
    Enforces state transitions, candidate-vs-truth confirmation, evidence linking,
    and deterministic deduplication.
    """

    ALLOWED_TRANSITIONS = {
        "REVIEW_REQUIRED": {"OPEN", "CANCELLED"},
        "OPEN": {"IN_PROGRESS", "COMPLETED", "CANCELLED"},
        "IN_PROGRESS": {"OPEN", "COMPLETED", "CANCELLED"},
        "COMPLETED": {"OPEN", "IN_PROGRESS"},
        "CANCELLED": {"OPEN", "REVIEW_REQUIRED"},
    }

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.temporal_resolver = TemporalResolver()
        self.candidate_resolver = OwnerCandidateResolver(db=db, tenant_id=tenant_id)

    @classmethod
    def compute_fingerprint(cls, tenant_id: UUID, meeting_id: UUID, title: str) -> str:
        """
        Deterministic hash preventing duplicate action items for the same task.
        """
        normalized_title = " ".join(title.strip().lower().split())
        raw_key = f"{tenant_id}:{meeting_id}:{normalized_title}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def ingest_llm_action_items(
        self,
        meeting_id: UUID,
        intelligence_run_id: UUID,
        items: List[Any],
        anchor_date: Optional[datetime] = None,
    ) -> List[ActionItem]:
        """
        Ingests a batch of LLMActionItemOutput models from intelligence extraction.
        """
        created_items = []
        for item in items:
            title = getattr(item, "title", str(item))
            description = getattr(item, "description", None)
            owner_raw = getattr(item, "raw_owner_text", getattr(item, "owner_raw", None))
            due_date_raw = getattr(item, "raw_due_date_text", getattr(item, "due_date_raw", None))
            priority = getattr(item, "priority", "MEDIUM")
            evidence_ids = getattr(item, "evidence_segment_ids", [])

            action_item = self.ingest_extracted_action_item(
                meeting_id=meeting_id,
                title=title,
                description=description,
                owner_raw=owner_raw,
                due_date_raw=due_date_raw,
                priority=priority,
                evidence_segment_ids=evidence_ids,
                intelligence_run_id=intelligence_run_id,
                anchor_date=anchor_date,
            )
            created_items.append(action_item)
        return created_items

    def ingest_extracted_action_item(
        self,
        meeting_id: UUID,
        title: str,
        description: Optional[str] = None,
        owner_raw: Optional[str] = None,
        due_date_raw: Optional[str] = None,
        priority: str = "MEDIUM",
        evidence_segment_ids: Optional[List[UUID]] = None,
        intelligence_run_id: Optional[UUID] = None,
        anchor_date: Optional[datetime] = None,
    ) -> ActionItem:
        """
        Ingests an AI-extracted action item with deduplication and candidate resolution.
        """
        fingerprint = self.compute_fingerprint(self.tenant_id, meeting_id, title)

        # Check existing item by fingerprint
        existing = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.tenant_id == self.tenant_id,
                ActionItem.meeting_id == meeting_id,
                ActionItem.fingerprint_hash == fingerprint,
            )
            .first()
        )

        if existing:
            # Append any new evidence anchors
            if evidence_segment_ids:
                existing_seg_ids = {e.segment_id for e in existing.evidence_items}
                for seg_id in evidence_segment_ids:
                    if seg_id not in existing_seg_ids:
                        evidence = ActionItemEvidence(
                            tenant_id=self.tenant_id,
                            action_item_id=existing.id,
                            segment_id=seg_id,
                        )
                        self.db.add(evidence)
                self.db.commit()
                self.db.refresh(existing)
            return existing

        # Resolve temporal due date
        resolved_due_date = self.temporal_resolver.resolve_expression(
            due_date_raw, anchor_date=anchor_date
        )

        # Resolve owner candidates
        cand_user_id, cand_spk_id, confidence = self.candidate_resolver.resolve_candidate(
            owner_raw=owner_raw, meeting_id=meeting_id
        )

        action_item = ActionItem(
            tenant_id=self.tenant_id,
            meeting_id=meeting_id,
            intelligence_run_id=intelligence_run_id,
            title=title.strip(),
            description=description,
            status="REVIEW_REQUIRED",
            priority=priority.upper() if priority else "MEDIUM",
            due_date=resolved_due_date,
            due_date_raw=due_date_raw,
            owner_raw=owner_raw,
            owner_candidate_user_id=cand_user_id,
            owner_candidate_speaker_id=cand_spk_id,
            owner_confidence=confidence,
            fingerprint_hash=fingerprint,
            is_confirmed=False,
        )
        self.db.add(action_item)
        self.db.flush()

        # Add evidence links
        if evidence_segment_ids:
            for seg_id in set(evidence_segment_ids):
                evidence = ActionItemEvidence(
                    tenant_id=self.tenant_id,
                    action_item_id=action_item.id,
                    segment_id=seg_id,
                )
                self.db.add(evidence)

        # Log creation audit event
        self._record_event(
            action_item=action_item,
            event_type="CREATED",
            new_state={
                "status": "REVIEW_REQUIRED",
                "title": action_item.title,
                "owner_raw": owner_raw,
                "candidate_user_id": str(cand_user_id) if cand_user_id else None,
            },
        )

        self.db.commit()
        self.db.refresh(action_item)
        return action_item

    def confirm_action_item(
        self,
        action_item_id: UUID,
        actor_user_id: Optional[UUID] = None,
        confirm_data: Optional[ActionItemConfirmRequest] = None,
    ) -> ActionItem:
        """
        Candidate vs. Truth transition: Promotes REVIEW_REQUIRED item to OPEN.
        Validates assigned user exists within the tenant.
        """
        item = self.get_action_item(action_item_id)
        if not item:
            raise ValueError(f"ActionItem {action_item_id} not found")

        prev_state = {
            "status": item.status,
            "owner_id": str(item.owner_id) if item.owner_id else None,
            "is_confirmed": item.is_confirmed,
        }

        # Determine owner
        target_owner_id = None
        if confirm_data and confirm_data.owner_id:
            # Validate tenant user
            owner = (
                self.db.query(User)
                .filter(User.id == confirm_data.owner_id, User.tenant_id == self.tenant_id)
                .first()
            )
            if not owner:
                raise ValueError("Specified owner_id does not belong to this enterprise tenant")
            target_owner_id = owner.id
        elif item.owner_candidate_user_id:
            target_owner_id = item.owner_candidate_user_id

        item.owner_id = target_owner_id
        item.is_confirmed = True
        item.status = "OPEN"

        if confirm_data:
            if confirm_data.title:
                item.title = confirm_data.title.strip()
            if confirm_data.due_date:
                item.due_date = confirm_data.due_date
            if confirm_data.priority:
                item.priority = confirm_data.priority

        new_state = {
            "status": item.status,
            "owner_id": str(item.owner_id) if item.owner_id else None,
            "is_confirmed": item.is_confirmed,
        }

        self._record_event(
            action_item=item,
            actor_user_id=actor_user_id,
            event_type="CONFIRMED",
            previous_state=prev_state,
            new_state=new_state,
        )

        self.db.commit()
        self.db.refresh(item)
        return item

    def transition_status(
        self,
        action_item_id: UUID,
        new_status: str,
        actor_user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> ActionItem:
        """
        Enforces state machine rules:
        REVIEW_REQUIRED -> OPEN -> IN_PROGRESS -> COMPLETED / CANCELLED
        """
        item = self.get_action_item(action_item_id)
        if not item:
            raise ValueError(f"ActionItem {action_item_id} not found")

        current = item.status
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition ActionItem from '{current}' to '{new_status}'. Allowed: {sorted(list(allowed))}"
            )

        prev_state = {"status": current}
        item.status = new_status
        if new_status == "COMPLETED":
            item.completed_at = datetime.now(timezone.utc)
        elif current == "COMPLETED" and new_status != "COMPLETED":
            item.completed_at = None

        new_state = {"status": new_status, "reason": reason}

        self._record_event(
            action_item=item,
            actor_user_id=actor_user_id,
            event_type="STATUS_CHANGED",
            previous_state=prev_state,
            new_state=new_state,
        )

        self.db.commit()
        self.db.refresh(item)
        return item

    def update_action_item(
        self,
        action_item_id: UUID,
        update_data: ActionItemUpdate,
        actor_user_id: Optional[UUID] = None,
    ) -> ActionItem:
        item = self.get_action_item(action_item_id)
        if not item:
            raise ValueError(f"ActionItem {action_item_id} not found")

        prev_state: Dict[str, Any] = {}
        new_state: Dict[str, Any] = {}

        if update_data.title is not None:
            prev_state["title"] = item.title
            item.title = update_data.title.strip()
            item.fingerprint_hash = self.compute_fingerprint(self.tenant_id, item.meeting_id, item.title)
            new_state["title"] = item.title

        if update_data.description is not None:
            item.description = update_data.description

        if update_data.priority is not None:
            prev_state["priority"] = item.priority
            item.priority = update_data.priority
            new_state["priority"] = item.priority

        if update_data.due_date is not None:
            prev_state["due_date"] = item.due_date.isoformat() if item.due_date else None
            item.due_date = update_data.due_date
            new_state["due_date"] = item.due_date.isoformat() if item.due_date else None

        if update_data.owner_id is not None:
            owner = (
                self.db.query(User)
                .filter(User.id == update_data.owner_id, User.tenant_id == self.tenant_id)
                .first()
            )
            if not owner:
                raise ValueError("Specified owner does not belong to this tenant")
            prev_state["owner_id"] = str(item.owner_id) if item.owner_id else None
            item.owner_id = owner.id
            new_state["owner_id"] = str(item.owner_id)

        self._record_event(
            action_item=item,
            actor_user_id=actor_user_id,
            event_type="UPDATED",
            previous_state=prev_state,
            new_state=new_state,
        )

        self.db.commit()
        self.db.refresh(item)
        return item

    def add_comment(
        self,
        action_item_id: UUID,
        user_id: UUID,
        comment_text: str,
    ) -> ActionItemComment:
        item = self.get_action_item(action_item_id)
        if not item:
            raise ValueError(f"ActionItem {action_item_id} not found")

        comment = ActionItemComment(
            tenant_id=self.tenant_id,
            action_item_id=action_item_id,
            user_id=user_id,
            comment_text=comment_text.strip(),
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_action_item(self, action_item_id: UUID) -> Optional[ActionItem]:
        return (
            self.db.query(ActionItem)
            .filter(
                ActionItem.id == action_item_id,
                ActionItem.tenant_id == self.tenant_id,
            )
            .first()
        )

    def list_meeting_action_items(
        self,
        meeting_id: UUID,
        status: Optional[str] = None,
        owner_id: Optional[UUID] = None,
    ) -> List[ActionItem]:
        query = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.tenant_id == self.tenant_id,
                ActionItem.meeting_id == meeting_id,
            )
        )
        if status:
            query = query.filter(ActionItem.status == status)
        if owner_id:
            query = query.filter(ActionItem.owner_id == owner_id)
        return query.order_by(desc(ActionItem.created_at)).all()

    def _record_event(
        self,
        action_item: ActionItem,
        event_type: str,
        actor_user_id: Optional[UUID] = None,
        previous_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
    ) -> ActionItemEvent:
        event = ActionItemEvent(
            tenant_id=self.tenant_id,
            action_item_id=action_item.id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
        )
        self.db.add(event)
        return event
