"""
Phase 24 – Graph Extraction Service

Extracts enterprise entities (Persons, Projects, Topics, Decisions, Actions) and
evidence-backed relationships from canonical meeting transcripts and intelligence records.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session
import structlog

from app.actions.models import ActionItem, ActionItemEvidence
from app.decisions.models import DecisionEvidence, DecisionRelationship, EnterpriseDecision
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.schemas import GraphExtractionResponse
from app.intelligence.cross_meeting.resolver import CrossMeetingResolver
from app.intelligence.models import Topic
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


class GraphExtractionService:
    """
    Constructs the organizational knowledge graph from canonical meeting artifacts.
    Guarantees that every relationship links back to exact transcript segment evidence.
    """

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.resolver = CrossMeetingResolver()

    def get_or_create_entity(
        self,
        name: str,
        entity_type: str,
        aliases: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> KnowledgeEntity:
        """Resolves or provisions an entity node, maintaining canonical name unification."""
        clean_name = name.strip()
        canonical = self.resolver.canonicalize(clean_name)
        new_aliases = list(aliases or [])
        if clean_name != canonical and clean_name not in new_aliases:
            new_aliases.append(clean_name)

        # 1. Search for existing entity by exact canonical name and entity_type in tenant
        existing = (
            self.db.query(KnowledgeEntity)
            .filter(
                KnowledgeEntity.tenant_id == self.tenant_id,
                KnowledgeEntity.entity_type == entity_type,
                KnowledgeEntity.canonical_name == canonical,
            )
            .first()
        )
        if existing:
            # Update aliases if novel
            curr_aliases = set(existing.aliases or [])
            updated = False
            for a in new_aliases:
                if a not in curr_aliases:
                    curr_aliases.add(a)
                    updated = True
            if updated:
                existing.aliases = list(curr_aliases)
                self.db.flush()
            return existing

        # 2. Check alias matches across entities
        all_entities = (
            self.db.query(KnowledgeEntity)
            .filter(
                KnowledgeEntity.tenant_id == self.tenant_id,
                KnowledgeEntity.entity_type == entity_type,
            )
            .all()
        )
        for ent in all_entities:
            if self.resolver.are_same_entity(clean_name, ent.canonical_name):
                curr_aliases = set(ent.aliases or [])
                curr_aliases.add(clean_name)
                ent.aliases = list(curr_aliases)
                self.db.flush()
                return ent

        # 3. Provision new entity node
        node = KnowledgeEntity(
            tenant_id=self.tenant_id,
            name=clean_name,
            canonical_name=canonical,
            entity_type=entity_type,
            aliases=new_aliases,
            metadata_json=metadata or {},
        )
        self.db.add(node)
        self.db.flush()
        return node

    def add_relationship_if_missing(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
        meeting_id: Optional[UUID] = None,
        evidence_segment_id: Optional[UUID] = None,
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> Optional[KnowledgeRelationship]:
        """Adds a directed, evidence-backed edge if it doesn't already exist."""
        if source_id == target_id:
            return None

        exists = (
            self.db.query(KnowledgeRelationship)
            .filter(
                KnowledgeRelationship.tenant_id == self.tenant_id,
                KnowledgeRelationship.source_entity_id == source_id,
                KnowledgeRelationship.target_entity_id == target_id,
                KnowledgeRelationship.relationship_type == rel_type,
            )
            .first()
        )
        if exists:
            return exists

        edge = KnowledgeRelationship(
            tenant_id=self.tenant_id,
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=rel_type,
            confidence=confidence,
            meeting_id=meeting_id,
            evidence_segment_id=evidence_segment_id,
            metadata_json=metadata or {},
        )
        self.db.add(edge)
        self.db.flush()
        return edge

    def extract_from_meeting(self, meeting_id: UUID) -> GraphExtractionResponse:
        """
        Ingests all intelligence records for a meeting and synthesizes graph nodes and edges.
        """
        meeting = (
            self.db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.tenant_id == self.tenant_id)
            .first()
        )
        if not meeting:
            return GraphExtractionResponse(
                meeting_id=meeting_id,
                entities_created=0,
                relationships_created=0,
                evidence_links_count=0,
            )

        entities_before = self.db.query(KnowledgeEntity).filter_by(tenant_id=self.tenant_id).count()
        edges_before = self.db.query(KnowledgeRelationship).filter_by(tenant_id=self.tenant_id).count()

        # 1. Create Meeting Entity Node
        meeting_node = self.get_or_create_entity(
            name=meeting.title,
            entity_type="MEETING",
            metadata={"meeting_id": str(meeting.id), "meeting_date": str(meeting.meeting_date)},
        )

        # 2. Extract Speakers & Participation Edges
        speakers = (
            self.db.query(Speaker)
            .filter(Speaker.meeting_id == meeting_id, Speaker.tenant_id == self.tenant_id)
            .all()
        )
        speaker_nodes: Dict[UUID, KnowledgeEntity] = {}

        for spk in speakers:
            spk_name = spk.display_name or spk.speaker_label
            p_node = self.get_or_create_entity(
                name=spk_name,
                entity_type="PERSON",
                aliases=[spk.speaker_label] if spk.display_name else [],
                metadata={"speaker_id": str(spk.id)},
            )
            speaker_nodes[spk.id] = p_node

            # Find speaker's first segment for evidence provenance
            first_seg = (
                self.db.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.speaker_id == spk.id,
                    TranscriptSegment.tenant_id == self.tenant_id,
                )
                .order_by(TranscriptSegment.start_seconds.asc())
                .first()
            )
            seg_id = first_seg.id if first_seg else None
            self.add_relationship_if_missing(
                source_id=p_node.id,
                target_id=meeting_node.id,
                rel_type="PARTICIPATED_IN",
                meeting_id=meeting_id,
                evidence_segment_id=seg_id,
            )

        # 3. Extract Topics & Discussion Edges
        topics = (
            self.db.query(Topic)
            .filter(Topic.meeting_id == meeting_id, Topic.tenant_id == self.tenant_id)
            .all()
        )
        for t in topics:
            t_node = self.get_or_create_entity(
                name=t.title,
                entity_type="TOPIC",
                metadata={"topic_id": str(t.id), "summary": t.summary},
            )
            t_evidence = UUID(str(t.evidence_segment_ids[0])) if t.evidence_segment_ids else None
            self.add_relationship_if_missing(
                source_id=meeting_node.id,
                target_id=t_node.id,
                rel_type="DISCUSSED",
                meeting_id=meeting_id,
                evidence_segment_id=t_evidence,
            )

        # 4. Extract Decisions & Attribution / Impact Edges
        decisions = (
            self.db.query(EnterpriseDecision)
            .filter(EnterpriseDecision.meeting_id == meeting_id, EnterpriseDecision.tenant_id == self.tenant_id)
            .all()
        )
        for d in decisions:
            d_node = self.get_or_create_entity(
                name=d.title,
                entity_type="DECISION",
                metadata={"decision_id": str(d.id), "status": d.status, "impact": d.impact_level},
            )
            d_evidence = UUID(str(d.evidence_segment_ids[0])) if d.evidence_segment_ids else None

            self.add_relationship_if_missing(
                source_id=meeting_node.id,
                target_id=d_node.id,
                rel_type="DECIDED_IN",
                meeting_id=meeting_id,
                evidence_segment_id=d_evidence,
            )

            # Decided by Person edge
            if d.decided_by_raw:
                p_node = self.get_or_create_entity(name=d.decided_by_raw, entity_type="PERSON")
                self.add_relationship_if_missing(
                    source_id=p_node.id,
                    target_id=d_node.id,
                    rel_type="DECIDED",
                    meeting_id=meeting_id,
                    evidence_segment_id=d_evidence,
                )

            # Decision Relationships (SUPERSEDES, REVERSES)
            d_rels = (
                self.db.query(DecisionRelationship)
                .filter(
                    DecisionRelationship.source_decision_id == d.id,
                    DecisionRelationship.tenant_id == self.tenant_id,
                )
                .all()
            )
            for r in d_rels:
                target_d = self.db.query(EnterpriseDecision).filter_by(id=r.target_decision_id).first()
                if target_d:
                    old_d_node = self.get_or_create_entity(name=target_d.title, entity_type="DECISION")
                    self.add_relationship_if_missing(
                        source_id=d_node.id,
                        target_id=old_d_node.id,
                        rel_type=r.relationship_type,
                        meeting_id=meeting_id,
                        evidence_segment_id=d_evidence,
                    )

        # 5. Extract Action Items & Ownership Edges
        actions = (
            self.db.query(ActionItem)
            .filter(ActionItem.meeting_id == meeting_id, ActionItem.tenant_id == self.tenant_id)
            .all()
        )
        for a in actions:
            a_node = self.get_or_create_entity(
                name=a.title,
                entity_type="ACTION",
                metadata={"action_id": str(a.id), "status": a.status, "priority": a.priority},
            )

            # Resolve evidence segment for action item
            a_ev = (
                self.db.query(ActionItemEvidence)
                .filter(ActionItemEvidence.action_item_id == a.id)
                .first()
            )
            a_seg_id = a_ev.segment_id if a_ev else None

            # Ownership edge: Person --OWNS--> Action
            if a.owner_raw:
                p_node = self.get_or_create_entity(name=a.owner_raw, entity_type="PERSON")
                self.add_relationship_if_missing(
                    source_id=p_node.id,
                    target_id=a_node.id,
                    rel_type="OWNS",
                    meeting_id=meeting_id,
                    evidence_segment_id=a_seg_id,
                )

            self.add_relationship_if_missing(
                source_id=a_node.id,
                target_id=meeting_node.id,
                rel_type="ARISES_FROM",
                meeting_id=meeting_id,
                evidence_segment_id=a_seg_id,
            )

        self.db.commit()

        entities_after = self.db.query(KnowledgeEntity).filter_by(tenant_id=self.tenant_id).count()
        edges_after = self.db.query(KnowledgeRelationship).filter_by(tenant_id=self.tenant_id).count()

        return GraphExtractionResponse(
            meeting_id=meeting_id,
            entities_created=entities_after - entities_before,
            relationships_created=edges_after - edges_before,
            evidence_links_count=edges_after - edges_before,
        )
