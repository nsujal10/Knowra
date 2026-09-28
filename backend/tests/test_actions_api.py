import pytest
from uuid import uuid4
from app.core.database import SessionLocal
from app.api.v1.actions import build_actions_response
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.user import User
from app.actions.models import ActionItem
from app.actions.service import ActionItemService

def test_build_actions_response_enterprise():
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
            title="Q4 Sprint Deliverables Review",
            status="COMPLETED",
        )
        db.add(meeting)
        db.flush()

        title = "Deploy and verify Kubernetes ingress controller"
        fp = ActionItemService.compute_fingerprint(tenant_id, meeting_id, title)
        action = ActionItem(
            id=uuid4(),
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            title=title,
            description="Configure cert-manager and SSL certificates on ingress.",
            status="OPEN",
            priority="HIGH",
            owner_raw="DevOps Lead",
            fingerprint_hash=fp,
            is_confirmed=True,
        )
        db.add(action)
        db.commit()

        # Call response builder
        res = build_actions_response(db, tenant_id=tenant_id, meeting_id=meeting_id)
        assert res.total == 1
        assert res.items[0].meeting_title == "Q4 Sprint Deliverables Review"
        assert res.items[0].status == "OPEN"
        assert res.items[0].priority == "HIGH"
        assert res.items[0].assignee == "DevOps Lead"
        assert res.metrics.total_items == 1
        assert res.metrics.pending_count == 1
        assert len(res.meetings) >= 1
        assert "DevOps Lead" in res.owners
    finally:
        db.rollback()
        # Cleanup
        db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()
        db.query(Meeting).filter(Meeting.id == meeting_id).delete()
        db.commit()
        db.close()
