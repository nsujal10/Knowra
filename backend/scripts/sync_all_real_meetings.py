"""
Knowra – Real Meetings Knowledge Graph Reconciler

Scans all real meetings in the database with their transcripts,
confirmed decisions, and action items, and populates the Knowledge Graph
so users can view real meeting lineages end-to-end.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.meeting import Meeting
from app.decisions.models import EnterpriseDecision
from app.actions.models import ActionItem
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.models.organization import Organization


def canonicalize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower().strip())[:100]


def sync_all_real_meetings():
    db: Session = SessionLocal()

    try:
        org = db.query(Organization).filter(Organization.name.ilike("%Softude%")).first()
        if not org:
            org = db.query(Organization).first()
        org_id = org.id

        meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
        print(f"[*] Scanning {len(meetings)} meetings in database...")

        new_ents = 0
        new_rels = 0

        for m in meetings:
            decs = db.query(EnterpriseDecision).filter(EnterpriseDecision.meeting_id == m.id).all()
            acts = db.query(ActionItem).filter(ActionItem.meeting_id == m.id).all()

            if not decs and not acts:
                continue

            # 1. Ensure meeting entity exists
            m_ent = db.query(KnowledgeEntity).filter(KnowledgeEntity.name == m.title).first()
            if not m_ent:
                m_ent = KnowledgeEntity(
                    id=uuid4(),
                    tenant_id=org_id,
                    name=m.title,
                    canonical_name=f"meeting_{canonicalize(m.title)}_{str(m.id)[:8]}",
                    entity_type="MEETING",
                    metadata_json={
                        "meeting_id": str(m.id),
                        "status": m.status or "COMPLETED",
                        "date": m.created_at.strftime("%b %d, %Y") if m.created_at else "Recent",
                    },
                )
                db.add(m_ent)
                db.flush()
                new_ents += 1

            # 2. Link decisions
            for d in decs:
                d_ent = db.query(KnowledgeEntity).filter(KnowledgeEntity.name == d.title).first()
                if not d_ent:
                    d_ent = KnowledgeEntity(
                        id=uuid4(),
                        tenant_id=org_id,
                        name=d.title,
                        canonical_name=f"decision_{canonicalize(d.title)}_{str(d.id)[:8]}",
                        entity_type="DECISION",
                        metadata_json={
                            "decision_id": str(d.id),
                            "status": d.status,
                            "impact": d.impact_level,
                            "decided_by": d.decided_by_raw or "Executive Leadership",
                            "rationale": d.rationale or d.description,
                        },
                    )
                    db.add(d_ent)
                    db.flush()
                    new_ents += 1

                # Meeting -> Decision
                rel = (
                    db.query(KnowledgeRelationship)
                    .filter(
                        KnowledgeRelationship.source_entity_id == m_ent.id,
                        KnowledgeRelationship.target_entity_id == d_ent.id,
                    )
                    .first()
                )
                if not rel:
                    db.add(
                        KnowledgeRelationship(
                            id=uuid4(),
                            tenant_id=org_id,
                            source_entity_id=m_ent.id,
                            target_entity_id=d_ent.id,
                            relationship_type="RECORDED_DECISION",
                            meeting_id=m.id,
                            confidence=1.0,
                            metadata_json={},
                        )
                    )
                    new_rels += 1

                # Decision -> Decided By Person
                if d.decided_by_raw:
                    person_name = d.decided_by_raw.strip()
                    p_ent = db.query(KnowledgeEntity).filter(KnowledgeEntity.name == person_name).first()
                    if not p_ent:
                        p_ent = KnowledgeEntity(
                            id=uuid4(),
                            tenant_id=org_id,
                            name=person_name,
                            canonical_name=f"person_{canonicalize(person_name)}",
                            entity_type="PERSON",
                            metadata_json={"role": "Decision Maker"},
                        )
                        db.add(p_ent)
                        db.flush()
                        new_ents += 1

                    rel_p = (
                        db.query(KnowledgeRelationship)
                        .filter(
                            KnowledgeRelationship.source_entity_id == d_ent.id,
                            KnowledgeRelationship.target_entity_id == p_ent.id,
                        )
                        .first()
                    )
                    if not rel_p:
                        db.add(
                            KnowledgeRelationship(
                                id=uuid4(),
                                tenant_id=org_id,
                                source_entity_id=d_ent.id,
                                target_entity_id=p_ent.id,
                                relationship_type="DECIDED_BY",
                                meeting_id=m.id,
                                confidence=0.99,
                                metadata_json={},
                            )
                        )
                        new_rels += 1

            # 3. Link action items
            for a in acts:
                a_ent = db.query(KnowledgeEntity).filter(KnowledgeEntity.name == a.title).first()
                if not a_ent:
                    a_ent = KnowledgeEntity(
                        id=uuid4(),
                        tenant_id=org_id,
                        name=a.title,
                        canonical_name=f"action_{canonicalize(a.title)}_{str(a.id)[:8]}",
                        entity_type="ACTION",
                        metadata_json={
                            "action_id": str(a.id),
                            "status": a.status,
                            "priority": a.priority or "HIGH",
                            "assignee": a.owner_raw or "Engineering Team",
                        },
                    )
                    db.add(a_ent)
                    db.flush()
                    new_ents += 1

                # Meeting -> Action
                rel = (
                    db.query(KnowledgeRelationship)
                    .filter(
                        KnowledgeRelationship.source_entity_id == m_ent.id,
                        KnowledgeRelationship.target_entity_id == a_ent.id,
                    )
                    .first()
                )
                if not rel:
                    db.add(
                        KnowledgeRelationship(
                            id=uuid4(),
                            tenant_id=org_id,
                            source_entity_id=m_ent.id,
                            target_entity_id=a_ent.id,
                            relationship_type="GENERATED_ACTION",
                            meeting_id=m.id,
                            confidence=1.0,
                            metadata_json={},
                        )
                    )
                    new_rels += 1

                # Action -> Assigned To Person
                if a.owner_raw:
                    assignee_name = a.owner_raw.strip()
                    p_ent = db.query(KnowledgeEntity).filter(KnowledgeEntity.name == assignee_name).first()
                    if not p_ent:
                        p_ent = KnowledgeEntity(
                            id=uuid4(),
                            tenant_id=org_id,
                            name=assignee_name,
                            canonical_name=f"person_{canonicalize(assignee_name)}",
                            entity_type="PERSON",
                            metadata_json={"role": "Action Owner"},
                        )
                        db.add(p_ent)
                        db.flush()
                        new_ents += 1

                    rel_a = (
                        db.query(KnowledgeRelationship)
                        .filter(
                            KnowledgeRelationship.source_entity_id == a_ent.id,
                            KnowledgeRelationship.target_entity_id == p_ent.id,
                        )
                        .first()
                    )
                    if not rel_a:
                        db.add(
                            KnowledgeRelationship(
                                id=uuid4(),
                                tenant_id=org_id,
                                source_entity_id=a_ent.id,
                                target_entity_id=p_ent.id,
                                relationship_type="ASSIGNED_TO",
                                meeting_id=m.id,
                                confidence=0.99,
                                metadata_json={},
                            )
                        )
                        new_rels += 1

        db.commit()
        print(f"[+] Reconciled Real Database Meetings: Added {new_ents} entities and {new_rels} relationships.")
        total_ents = db.query(KnowledgeEntity).count()
        total_rels = db.query(KnowledgeRelationship).count()
        print(f"[*] Current Total Knowledge Graph State: {total_ents} entities, {total_rels} relationships.")

    except Exception as e:
        db.rollback()
        print(f"[-] Error reconciling meetings: {e}", file=sys.stderr)
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    sync_all_real_meetings()
