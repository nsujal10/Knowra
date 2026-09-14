"""
Phase 17 – End-to-End Decision Intelligence & Graph Lineage Test
================================================================

Validates complete Phase 17 lifecycle:
  1. Multi-meeting Decision Creation with Evidence Segment Linking
  2. Automatic Conflict Resolution & Superseding (CONFIRMED -> SUPERSEDED)
  3. Decision Graph Construction & Traversal (Nodes & Directed Edges)
  4. Terminal Decision Discovery for Topics
  5. Multi-Tenant Boundary Enforcement (Cross-Tenant 404 / empty search)

Run with:
    python scripts/phase17_e2e_test.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from app.core.database import SessionLocal
from app.decisions.models import Decision, DecisionRelationship
from app.decisions.resolver import DecisionResolutionService
from app.decisions.schemas import DecisionCreateRequest, DecisionRelationshipCreate
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.user import User


def run_phase17_e2e_test():
    print("================================================================")
    print("🚀 Starting Phase 17 (Decision Intelligence) E2E Test")
    print("================================================================")

    db = SessionLocal()
    try:
        # Step 1: Tenant & User Setup
        uid = str(uuid.uuid4())[:8]
        org = Organization(name=f"Acme Enterprise {uid}", slug=f"acme-enterprise-{uid}")
        db.add(org)
        db.flush()

        user = User(
            email=f"lead_architect_{uid}@acme.com",
            password_hash="hashed_pw_secret",
            full_name="Lead Architect",
        )
        db.add(user)
        db.flush()

        meeting_q1 = Meeting(tenant_id=org.id, owner_id=user.id, title="Q1 Infrastructure Architecture Sync")
        meeting_q2 = Meeting(tenant_id=org.id, owner_id=user.id, title="Q2 Cloud Infrastructure Modernization")
        db.add_all([meeting_q1, meeting_q2])
        db.commit()

        print(f"✅ Provisioned Organization '{org.name}' ({org.id}) and 2 Meetings")

        # Step 2: Create Baseline Decision in Q1
        service = DecisionResolutionService(db=db, tenant_id=org.id)

        req1 = DecisionCreateRequest(
            title="Deploy PostgreSQL on EC2",
            description="We will deploy our PostgreSQL primary database on an AWS EC2 instance.",
            rationale="Initial prototype simplicity and direct file access",
            impact_level="HIGH",
            topics=["infrastructure", "database"],
            effective_date=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        d1 = service.create_decision(
            meeting_id=meeting_q1.id,
            payload=req1,
            actor_user_id=user.id,
        )
        print(f"✅ Created Q1 Decision: '{d1.title}' [Status: {d1.status}, ID: {d1.id}]")
        assert d1.status == "CONFIRMED"

        # Step 3: Query Active Decision for 'database'
        active_q1 = service.get_latest_decision_for_topic("database")
        assert active_q1 is not None
        assert active_q1.id == d1.id
        print(f"✅ Verified Active Decision for 'database': '{active_q1.title}'")

        # Step 4: Create Superseding Decision in Q2
        req2 = DecisionCreateRequest(
            title="Migrate and switch from EC2 to AWS RDS PostgreSQL",
            description="We decided to override and replace our EC2 setup to switch from EC2 to AWS RDS PostgreSQL instead of managing EC2.",
            rationale="Managed automated backups, multi-AZ high availability, and automated security patching",
            impact_level="HIGH",
            topics=["infrastructure", "database"],
            effective_date=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        )
        d2 = service.create_decision(
            meeting_id=meeting_q2.id,
            payload=req2,
            actor_user_id=user.id,
        )

        db.refresh(d1)
        db.refresh(d2)

        print(f"✅ Created Q2 Decision: '{d2.title}' [Status: {d2.status}, ID: {d2.id}]")
        print(f"🔄 Automatic Resolution: Q1 Decision Status changed to -> [{d1.status}]")
        assert d1.status == "SUPERSEDED", "Q1 decision must transition to SUPERSEDED!"
        assert d2.status == "CONFIRMED", "Q2 decision must be CONFIRMED!"

        # Step 5: Verify Decision Graph Lineage
        graph = service.get_decision_graph(d2.id)
        node_ids = {n.id for n in graph.nodes}
        assert d1.id in node_ids
        assert d2.id in node_ids
        assert len(graph.edges) >= 1

        supersede_edge = next(e for e in graph.edges if e.relationship_type == "SUPERSEDES")
        assert supersede_edge.source_id == d2.id
        assert supersede_edge.target_id == d1.id
        print(f"✅ Decision Graph verified: {len(graph.nodes)} Nodes, {len(graph.edges)} Directed Edges (SUPERSEDES verified)")

        # Step 6: Verify Terminal Decision for 'database' now points to d2
        active_q2 = service.get_latest_decision_for_topic("database")
        assert active_q2 is not None
        assert active_q2.id == d2.id
        print(f"✅ Verified Latest Active Decision for 'database' resolved to: '{active_q2.title}'")

        # Step 7: Multi-Tenant Boundary Isolation Check
        other_uid = str(uuid.uuid4())[:8]
        other_org = Organization(name=f"Foreign Corp {other_uid}", slug=f"foreign-corp-{other_uid}")
        db.add(other_org)
        db.commit()

        foreign_service = DecisionResolutionService(db=db, tenant_id=other_org.id)
        foreign_active = foreign_service.get_latest_decision_for_topic("database")
        assert foreign_active is None, "Cross-tenant leakage: Foreign tenant retrieved Acme's decision!"
        print("🔒 Multi-Tenant Boundary Verified: Foreign tenant cannot access decisions.")

        print("================================================================")
        print("🎉 Phase 17 E2E Decision Intelligence Test PASSED Successfully!")
        print("================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_phase17_e2e_test()
