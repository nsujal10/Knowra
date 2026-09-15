"""
Phase 23 – Timeline Builder Service

Assembles chronological events, decisions, and action items across disparate meetings
while maintaining segment-level evidence provenance and strict authorization boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session

from app.actions.models import ActionItem
from app.auth.scope import AuthorizedRetrievalScope
from app.decisions.models import DecisionRelationship, EnterpriseDecision
from app.intelligence.cross_meeting.resolver import CrossMeetingResolver
from app.intelligence.cross_meeting.schemas import (
    DecisionEvolutionNode,
    DecisionEvolutionResponse,
    TimelineEvent,
    TimelineResponse,
)
from app.intelligence.models import Topic
from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment


class TimelineBuilder:
    """
    Builds structured, chronologically ordered timelines spanning multiple meetings.
    Enforces push-down authorization constraints via AuthorizedRetrievalScope.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.resolver = CrossMeetingResolver()

    def build_timeline(
        self,
        scope: AuthorizedRetrievalScope,
        entity_or_topic: str,
        meeting_ids: Optional[List[UUID]] = None,
        limit: int = 50,
    ) -> TimelineResponse:
        """
        Assembles chronological events matching an entity/topic across authorized meetings.
        Orders by meeting_date ASC, then timestamp_seconds ASC.
        """
        tenant_id = scope.tenant_id
        canonical_target = self.resolver.canonicalize(entity_or_topic)

        # 1. Resolve permitted meeting IDs
        effective_meetings = scope.allowed_meeting_ids
        if meeting_ids is not None:
            if effective_meetings is not None:
                effective_meetings = set(meeting_ids) & effective_meetings
            else:
                effective_meetings = set(meeting_ids)

        if effective_meetings is not None and len(effective_meetings) == 0:
            return TimelineResponse(
                entity_or_topic=canonical_target,
                total_events=0,
                meetings_covered=0,
                events=[],
            )

        # 2. Query Meetings Map
        m_query = self.db.query(Meeting).filter(Meeting.tenant_id == tenant_id)
        if effective_meetings is not None:
            m_query = m_query.filter(Meeting.id.in_(list(effective_meetings)))
        meetings = m_query.all()
        meeting_map = {m.id: m for m in meetings}
        meeting_id_list = list(meeting_map.keys())

        if not meeting_id_list:
            return TimelineResponse(
                entity_or_topic=canonical_target,
                total_events=0,
                meetings_covered=0,
                events=[],
            )

        events: List[TimelineEvent] = []

        # 3. Retrieve Topics across meetings
        topics = (
            self.db.query(Topic)
            .filter(
                Topic.tenant_id == tenant_id,
                Topic.meeting_id.in_(meeting_id_list),
            )
            .all()
        )
        for t in topics:
            if self.resolver.are_same_entity(t.title, entity_or_topic) or (
                entity_or_topic.lower() in (t.summary or "").lower()
            ):
                m = meeting_map.get(t.meeting_id)
                m_title = m.title if m else "Unknown Meeting"
                m_date = m.meeting_date if m and m.meeting_date else (m.created_at if m else None)
                events.append(
                    TimelineEvent(
                        event_id=t.id,
                        meeting_id=t.meeting_id,
                        meeting_title=m_title,
                        meeting_date=m_date,
                        timestamp_seconds=t.start_seconds or 0.0,
                        event_type="TOPIC",
                        title=t.title,
                        description=t.summary or "",
                        status="DISCUSSED",
                        evidence_segment_ids=t.evidence_segment_ids or [],
                    )
                )

        # 4. Retrieve Decisions across meetings
        decisions = (
            self.db.query(EnterpriseDecision)
            .filter(
                EnterpriseDecision.tenant_id == tenant_id,
                EnterpriseDecision.meeting_id.in_(meeting_id_list),
            )
            .all()
        )
        for d in decisions:
            text_bundle = f"{d.title} {d.description} {d.rationale or ''}"
            if self.resolver.are_same_entity(d.title, entity_or_topic) or (
                entity_or_topic.lower() in text_bundle.lower()
            ):
                m = meeting_map.get(d.meeting_id)
                m_title = m.title if m else "Unknown Meeting"
                m_date = m.meeting_date if m and m.meeting_date else (m.created_at if m else None)
                events.append(
                    TimelineEvent(
                        event_id=d.id,
                        meeting_id=d.meeting_id,
                        meeting_title=m_title,
                        meeting_date=m_date,
                        timestamp_seconds=0.0,
                        event_type="DECISION",
                        title=d.title,
                        description=d.description,
                        speaker_name=d.decided_by_raw,
                        status=d.status,
                        evidence_segment_ids=d.evidence_segment_ids or [],
                    )
                )

        # 5. Retrieve Action Items across meetings
        actions = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.tenant_id == tenant_id,
                ActionItem.meeting_id.in_(meeting_id_list),
            )
            .all()
        )
        for a in actions:
            text_bundle = f"{a.title} {a.description or ''}"
            if self.resolver.are_same_entity(a.title, entity_or_topic) or (
                entity_or_topic.lower() in text_bundle.lower()
            ):
                m = meeting_map.get(a.meeting_id)
                m_title = m.title if m else "Unknown Meeting"
                m_date = m.meeting_date if m and m.meeting_date else (m.created_at if m else None)
                events.append(
                    TimelineEvent(
                        event_id=a.id,
                        meeting_id=a.meeting_id,
                        meeting_title=m_title,
                        meeting_date=m_date,
                        timestamp_seconds=0.0,
                        event_type="ACTION",
                        title=a.title,
                        description=a.description or "",
                        speaker_name=a.owner_raw,
                        status=a.status,
                    )
                )

        # 6. Sort Chronologically
        # Default meeting date if missing is UNIX epoch
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

        def event_sort_key(ev: TimelineEvent):
            d = ev.meeting_date or epoch
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return (d, ev.timestamp_seconds)

        events.sort(key=event_sort_key)
        selected_events = events[:limit]
        unique_meetings = {e.meeting_id for e in selected_events}

        return TimelineResponse(
            entity_or_topic=canonical_target,
            total_events=len(selected_events),
            meetings_covered=len(unique_meetings),
            events=selected_events,
        )

    def build_decision_evolution(
        self,
        scope: AuthorizedRetrievalScope,
        decision_id: UUID,
    ) -> DecisionEvolutionResponse:
        """
        Traces the longitudinal lifecycle of an enterprise decision across meetings,
        traversing SUPERSEDES, REVERSES, and REFINES relationships.
        """
        tenant_id = scope.tenant_id

        root = (
            self.db.query(EnterpriseDecision)
            .filter(
                EnterpriseDecision.id == decision_id,
                EnterpriseDecision.tenant_id == tenant_id,
            )
            .first()
        )
        if not root:
            return DecisionEvolutionResponse(
                root_decision_id=decision_id,
                total_versions=0,
                current_active_decision_id=None,
                evolution_chain=[],
            )

        # Breadth-first traversal of relationships
        chain_ids = [decision_id]
        visited = {decision_id}

        # Check relationships where root is source or target
        rels = (
            self.db.query(DecisionRelationship)
            .filter(
                DecisionRelationship.tenant_id == tenant_id,
                (DecisionRelationship.source_decision_id == decision_id)
                | (DecisionRelationship.target_decision_id == decision_id),
            )
            .all()
        )
        for r in rels:
            for did in (r.source_decision_id, r.target_decision_id):
                if did not in visited:
                    visited.add(did)
                    chain_ids.append(did)

        # Fetch all decisions in chain
        chain_decisions = (
            self.db.query(EnterpriseDecision)
            .filter(
                EnterpriseDecision.id.in_(chain_ids),
                EnterpriseDecision.tenant_id == tenant_id,
            )
            .all()
        )

        nodes: List[DecisionEvolutionNode] = []
        active_id = None

        # Build map of relationships for labeling
        rel_map = {}
        for r in rels:
            rel_map[r.source_decision_id] = (r.relationship_type, r.target_decision_id)

        for d in chain_decisions:
            if not scope.can_access_meeting(d.meeting_id):
                continue

            m = self.db.query(Meeting).filter(Meeting.id == d.meeting_id).first()
            m_title = m.title if m else "Meeting"
            m_date = m.meeting_date if m and m.meeting_date else (m.created_at if m else None)

            rel_type, rel_target = rel_map.get(d.id, ("ORIGINAL" if d.id == decision_id else "RELATED", None))
            if d.status == "CONFIRMED" and not active_id:
                active_id = d.id

            nodes.append(
                DecisionEvolutionNode(
                    decision_id=d.id,
                    meeting_id=d.meeting_id,
                    meeting_title=m_title,
                    meeting_date=m_date,
                    title=d.title,
                    description=d.description,
                    status=d.status,
                    relationship_type=rel_type,
                    related_decision_id=rel_target,
                    evidence_segment_ids=d.evidence_segment_ids or [],
                )
            )

        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        nodes.sort(key=lambda n: (n.meeting_date.replace(tzinfo=timezone.utc) if n.meeting_date and n.meeting_date.tzinfo is None else (n.meeting_date or epoch)))

        return DecisionEvolutionResponse(
            root_decision_id=decision_id,
            total_versions=len(nodes),
            current_active_decision_id=active_id or (nodes[-1].decision_id if nodes else None),
            evolution_chain=nodes,
        )
