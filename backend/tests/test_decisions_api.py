import pytest
from uuid import uuid4
from app.core.database import SessionLocal
from app.api.v1.decisions import build_decisions_response
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.user import User
from app.decisions.models import EnterpriseDecision, DecisionTopic

def test_build_decisions_response_enterprise():
    db = SessionLocal()
    meeting_id = uuid4()
    org = db.query(Organization).first()
    assert org is not None, "Organization fixture required"
    tenant_id = org.id

    try:
        user = db.query(User).first()
        owner_id = user.id if user else uuid4()

        meeting = Meeting(
            id=meeting_id,
            owner_id=owner_id,
            tenant_id=tenant_id,
            title="Executive Architecture Summit",
            status="COMPLETED",
        )
        db.add(meeting)

        decision = EnterpriseDecision(
            id=uuid4(),
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            intelligence_run_id=None,
            title="Adopt PostgreSQL with pgvector for knowledge storage",
            description="The engineering committee confirmed PostgreSQL with pgvector as our core vector store.",
            impact_level="HIGH",
            status="CONFIRMED",
            decided_by_raw="Chief Architect",
            fingerprint=f"fp-{uuid4()}",
            evidence_segment_ids=[],
        )
        db.add(decision)
        db.flush()

        db.add(DecisionTopic(
            id=uuid4(),
            tenant_id=tenant_id,
            decision_id=decision.id,
            topic_name="architecture",
        ))
        db.commit()

        # Call response builder
        res = build_decisions_response(db, tenant_id=tenant_id, meeting_id=meeting_id)
        assert res.total == 1
        assert res.items[0].meeting_title == "Executive Architecture Summit"
        assert res.items[0].status == "APPROVED"
        assert res.items[0].category == "ARCHITECTURE"
        assert res.metrics.total_decisions == 1
        assert "100%" in res.metrics.consensus_level
        assert len(res.meetings) >= 1
    finally:
        db.rollback()
        # Cleanup
        db.query(DecisionTopic).filter(DecisionTopic.tenant_id == tenant_id).delete()
        db.query(EnterpriseDecision).filter(EnterpriseDecision.meeting_id == meeting_id).delete()
        db.query(Meeting).filter(Meeting.id == meeting_id).delete()
        db.commit()
        db.close()
