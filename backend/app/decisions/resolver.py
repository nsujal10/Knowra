"""
Phase 17 – Decision Resolution Service

Implements:
  1. Semantic & lexical similarity calculation between decisions.
  2. Temporal reasoning: determining which decision is newer.
  3. Automatic relationship inference (SUPERSEDES, REFINES, REVERSES).
  4. Decision graph maintenance & latest active decision discovery.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

import structlog
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.decisions.models import (
    Decision,
    DecisionEvent,
    DecisionEvidence,
    DecisionRelationship,
    DecisionTopic,
)
from app.decisions.schemas import (
    DecisionCreateRequest,
    DecisionGraphEdge,
    DecisionGraphNode,
    DecisionGraphResponse,
    DecisionRelationshipCreate,
)
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


class DecisionResolutionService:
    """
    Core engine managing the organizational decision graph.
    Resolves conflicting decisions, links superseded records, and determines
    the current canonical decision for a given business topic or query.
    """

    SIMILARITY_THRESHOLD = 0.65  # Threshold for considering decisions related to the same topic

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    def compute_fingerprint(tenant_id: UUID, meeting_id: UUID, title: str) -> str:
        """Deterministic fingerprint preventing duplicate decisions in the same meeting."""
        normalized = " ".join(title.strip().lower().split())
        raw = f"{tenant_id}:{meeting_id}:{normalized}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_keywords(text: str) -> Set[str]:
        """Tokenize text into lowercase keywords filtering common stop words."""
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "over", "after",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "we", "they", "it", "our", "their", "will", "would", "should", "could",
        }
        words = re.findall(r"\b[a-z0-9_]{3,}\b", text.lower())
        return {w for w in words if w not in stopwords}

    def calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        """Jaccard keyword similarity between two text snippets."""
        set_a = self.extract_keywords(text_a)
        set_b = self.extract_keywords(text_b)
        if not set_a or not set_b:
            return 0.0
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        return len(intersection) / len(union)

    def create_decision(
        self,
        meeting_id: UUID,
        payload: DecisionCreateRequest,
        intelligence_run_id: Optional[UUID] = None,
        actor_user_id: Optional[UUID] = None,
    ) -> Decision:
        """
        Creates a new decision with evidence segments, runs resolution against historical decisions,
        and records an immutable creation event.
        """
        fingerprint = self.compute_fingerprint(self.tenant_id, meeting_id, payload.title)

        # Check existing decision by fingerprint to ensure idempotency
        existing = (
            self.db.query(Decision)
            .filter(
                Decision.tenant_id == self.tenant_id,
                Decision.meeting_id == meeting_id,
                Decision.fingerprint == fingerprint,
            )
            .first()
        )
        if existing:
            return existing

        decision = Decision(
            tenant_id=self.tenant_id,
            meeting_id=meeting_id,
            intelligence_run_id=intelligence_run_id,
            title=payload.title,
            description=payload.description,
            rationale=payload.rationale,
            status="CONFIRMED",
            impact_level=payload.impact_level,
            decided_by_raw=payload.decided_by_raw,
            decided_by_user_id=payload.decided_by_user_id,
            fingerprint=fingerprint,
            evidence_segment_ids=[str(s) for s in payload.evidence_segment_ids],
            effective_date=payload.effective_date or datetime.now(timezone.utc),
        )
        self.db.add(decision)
        self.db.flush()

        # Link evidence segments
        for seg_id in payload.evidence_segment_ids:
            seg = (
                self.db.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.id == seg_id,
                    TranscriptSegment.tenant_id == self.tenant_id,
                )
                .first()
            )
            snippet = seg.text if seg else None
            self.db.add(
                DecisionEvidence(
                    tenant_id=self.tenant_id,
                    decision_id=decision.id,
                    segment_id=seg_id,
                    snippet=snippet,
                )
            )

        # Link topic tags
        for topic_str in payload.topics:
            self.db.add(
                DecisionTopic(
                    tenant_id=self.tenant_id,
                    decision_id=decision.id,
                    topic_name=topic_str.strip().lower(),
                )
            )

        # Audit Event
        self.db.add(
            DecisionEvent(
                tenant_id=self.tenant_id,
                decision_id=decision.id,
                actor_user_id=actor_user_id,
                event_type="CREATED",
                new_state={"title": decision.title, "status": decision.status},
            )
        )
        self.db.flush()

        # Automatic cross-meeting resolution against historical decisions
        self.resolve_historical_conflicts(decision, actor_user_id=actor_user_id)

        self.db.commit()
        self.db.refresh(decision)
        return decision

    def resolve_historical_conflicts(
        self,
        new_decision: Decision,
        actor_user_id: Optional[UUID] = None,
    ) -> List[DecisionRelationship]:
        """
        Compares new decision against historical decisions within the same tenant.
        Detects semantic similarity and temporal ordering:
          - If new decision indicates a change/override or shares high topic similarity:
            marks relationship as SUPERSEDES or REFINES and transitions historical status to SUPERSEDED.
        """
        historical_decisions = (
            self.db.query(Decision)
            .filter(
                Decision.tenant_id == self.tenant_id,
                Decision.id != new_decision.id,
                Decision.status == "CONFIRMED",
            )
            .all()
        )

        created_relationships = []
        new_text = f"{new_decision.title} {new_decision.description} {new_decision.rationale or ''}".lower()

        # Keywords suggesting superseding or reversing
        is_override_cue = any(
            cue in new_text
            for cue in [
                "instead of", "replace", "override", "supersede", "cancel",
                "switch from", "pivot from", "revert", "no longer", "update decision"
            ]
        )

        for old in historical_decisions:
            old_text = f"{old.title} {old.description} {old.rationale or ''}".lower()
            similarity = self.calculate_text_similarity(new_text, old_text)

            # Check matching explicit topic tags
            old_topic_names = {t.topic_name for t in old.topics}
            new_topic_names = {t.topic_name for t in new_decision.topics}
            topic_overlap = bool(old_topic_names.intersection(new_topic_names))

            # Trigger condition:
            # High lexical similarity, OR topic overlap with override cue, OR topic overlap with >= 0.1 keyword similarity
            is_related = (
                similarity >= self.SIMILARITY_THRESHOLD
                or (topic_overlap and (is_override_cue or similarity >= 0.1))
            )

            if is_related:
                # Temporal comparison: if new_decision created_at or effective_date is newer
                new_time = new_decision.effective_date or new_decision.created_at
                old_time = old.effective_date or old.created_at

                if new_time >= old_time:
                    rel_type = "SUPERSEDES" if is_override_cue or similarity >= 0.7 else "REFINES"

                    # Create relationship
                    rel = DecisionRelationship(
                        tenant_id=self.tenant_id,
                        source_decision_id=new_decision.id,
                        target_decision_id=old.id,
                        relationship_type=rel_type,
                        confidence_score=round(similarity, 3),
                        reasoning=f"Automatic resolution: similarity={similarity:.2f}, cue={is_override_cue}",
                    )
                    self.db.add(rel)
                    created_relationships.append(rel)

                    if rel_type == "SUPERSEDES":
                        old_prev_status = old.status
                        old.status = "SUPERSEDED"
                        self.db.add(
                            DecisionEvent(
                                tenant_id=self.tenant_id,
                                decision_id=old.id,
                                actor_user_id=actor_user_id,
                                event_type="STATUS_CHANGED",
                                previous_state={"status": old_prev_status},
                                new_state={
                                    "status": "SUPERSEDED",
                                    "superseded_by": str(new_decision.id),
                                },
                            )
                        )
                        logger.info(
                            "Decision superseded by newer decision",
                            old_id=str(old.id),
                            new_id=str(new_decision.id),
                            rel_type=rel_type,
                        )

        return created_relationships

    def add_manual_relationship(
        self,
        source_decision_id: UUID,
        payload: DecisionRelationshipCreate,
        actor_user_id: Optional[UUID] = None,
    ) -> DecisionRelationship:
        """Manually links two decisions in the graph and updates state if SUPERSEDES/REVERSES."""
        source = (
            self.db.query(Decision)
            .filter(
                Decision.id == source_decision_id,
                Decision.tenant_id == self.tenant_id,
            )
            .first()
        )
        target = (
            self.db.query(Decision)
            .filter(
                Decision.id == payload.target_decision_id,
                Decision.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not source or not target:
            raise ValueError("Source or target decision not found or tenant unauthorized.")

        rel = DecisionRelationship(
            tenant_id=self.tenant_id,
            source_decision_id=source.id,
            target_decision_id=target.id,
            relationship_type=payload.relationship_type.upper(),
            confidence_score=payload.confidence_score,
            reasoning=payload.reasoning,
        )
        self.db.add(rel)

        if payload.relationship_type.upper() in {"SUPERSEDES", "REVERSES"}:
            prev_status = target.status
            new_status = "SUPERSEDED" if payload.relationship_type.upper() == "SUPERSEDES" else "REVERSED"
            target.status = new_status
            self.db.add(
                DecisionEvent(
                    tenant_id=self.tenant_id,
                    decision_id=target.id,
                    actor_user_id=actor_user_id,
                    event_type="STATUS_CHANGED",
                    previous_state={"status": prev_status},
                    new_state={"status": new_status, "related_to": str(source.id)},
                )
            )

        self.db.commit()
        self.db.refresh(rel)
        return rel

    def get_latest_decision_for_topic(self, topic_or_query: str) -> Optional[Decision]:
        """
        Finds the current, active (CONFIRMED) decision that governs a given topic or query,
        tracing graph relationships to return the terminal leaf if superseded.
        """
        keywords = self.extract_keywords(topic_or_query)
        query_topic = topic_or_query.strip().lower()

        # 1. Match by explicit topic tag first
        decisions_by_topic = (
            self.db.query(Decision)
            .join(DecisionTopic, DecisionTopic.decision_id == Decision.id)
            .filter(
                Decision.tenant_id == self.tenant_id,
                or_(
                    DecisionTopic.topic_name == query_topic,
                    DecisionTopic.topic_name.in_(keywords),
                ),
            )
            .order_by(desc(Decision.created_at))
            .all()
        )

        candidates = decisions_by_topic

        # 2. If no topic match, match by keyword in title/description
        if not candidates:
            all_decisions = (
                self.db.query(Decision)
                .filter(Decision.tenant_id == self.tenant_id)
                .order_by(desc(Decision.created_at))
                .all()
            )
            candidates = [
                d for d in all_decisions
                if self.calculate_text_similarity(topic_or_query, f"{d.title} {d.description}") > 0.15
            ]

        if not candidates:
            return None

        # Sort candidates preferring CONFIRMED over SUPERSEDED, then newest
        sorted_candidates = sorted(
            candidates,
            key=lambda d: (1 if d.status == "CONFIRMED" else 0, d.created_at),
            reverse=True,
        )

        root = sorted_candidates[0]

        # Trace outgoing SUPERSEDES edges to reach the ultimate active decision
        return self._resolve_terminal_decision(root)

    def _resolve_terminal_decision(self, decision: Decision) -> Decision:
        """Traverse SUPERSEDES relationships to find the ultimate active successor."""
        visited = {decision.id}
        curr = decision
        while curr.status in {"SUPERSEDED", "REVERSED"}:
            # Find which decision superseded this one (where target == curr.id and type == SUPERSEDES)
            successor_rel = (
                self.db.query(DecisionRelationship)
                .filter(
                    DecisionRelationship.target_decision_id == curr.id,
                    DecisionRelationship.relationship_type == "SUPERSEDES",
                    DecisionRelationship.tenant_id == self.tenant_id,
                )
                .first()
            )
            if not successor_rel or successor_rel.source_decision_id in visited:
                break
            visited.add(successor_rel.source_decision_id)
            succ = (
                self.db.query(Decision)
                .filter(Decision.id == successor_rel.source_decision_id)
                .first()
            )
            if not succ:
                break
            curr = succ
        return curr

    def get_decision_graph(self, decision_id: UUID) -> DecisionGraphResponse:
        """Retrieves graph nodes and edges connected to this decision (ancestors & descendants)."""
        nodes_dict: Dict[UUID, DecisionGraphNode] = {}
        edges: List[DecisionGraphEdge] = []

        to_explore = [decision_id]
        seen = set()

        while to_explore:
            curr_id = to_explore.pop(0)
            if curr_id in seen:
                continue
            seen.add(curr_id)

            d = (
                self.db.query(Decision)
                .filter(Decision.id == curr_id, Decision.tenant_id == self.tenant_id)
                .first()
            )
            if not d:
                continue

            nodes_dict[d.id] = DecisionGraphNode(
                id=d.id,
                title=d.title,
                status=d.status,
                impact_level=d.impact_level,
                created_at=d.created_at,
            )

            # Outgoing edges
            out_rels = (
                self.db.query(DecisionRelationship)
                .filter(DecisionRelationship.source_decision_id == curr_id)
                .all()
            )
            for r in out_rels:
                edges.append(
                    DecisionGraphEdge(
                        source_id=r.source_decision_id,
                        target_id=r.target_decision_id,
                        relationship_type=r.relationship_type,
                        reasoning=r.reasoning,
                    )
                )
                if r.target_decision_id not in seen:
                    to_explore.append(r.target_decision_id)

            # Incoming edges
            in_rels = (
                self.db.query(DecisionRelationship)
                .filter(DecisionRelationship.target_decision_id == curr_id)
                .all()
            )
            for r in in_rels:
                edges.append(
                    DecisionGraphEdge(
                        source_id=r.source_decision_id,
                        target_id=r.target_decision_id,
                        relationship_type=r.relationship_type,
                        reasoning=r.reasoning,
                    )
                )
                if r.source_decision_id not in seen:
                    to_explore.append(r.source_decision_id)

        # Deduplicate edges
        unique_edges = []
        edge_keys = set()
        for e in edges:
            key = (e.source_id, e.target_id, e.relationship_type)
            if key not in edge_keys:
                edge_keys.add(key)
                unique_edges.append(e)

        return DecisionGraphResponse(
            nodes=list(nodes_dict.values()),
            edges=unique_edges,
        )
