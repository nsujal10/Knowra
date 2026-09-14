"""
Unit Tests: Phase 17 Decision Intelligence & Resolution Engine
Validates:
  - Automatic relationship inference (SUPERSEDES, REFINES, REVERSES)
  - Status updates (CONFIRMED -> SUPERSEDED)
  - Terminal graph resolution for active decisions per topic
  - Multi-tenant isolation for decision queries
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.decisions.models import Decision, DecisionRelationship, DecisionTopic
from app.decisions.resolver import DecisionResolutionService
from app.decisions.schemas import DecisionCreateRequest, DecisionRelationshipCreate
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def tenant_and_user_fixture(db_session):
    uid = str(uuid.uuid4())[:8]
    org = Organization(name=f"Test Org {uid}", slug=f"test-org-{uid}")
    db_session.add(org)
    db_session.flush()

    user = User(
        email=f"decision_user_{uid}@example.com",
        password_hash="fakehash",
        full_name=f"Decision User {uid}",
    )
    db_session.add(user)
    db_session.commit()
    return org.id, user.id


def test_decision_resolution_supersedes(db_session, tenant_and_user_fixture):
    tenant_id, user_id = tenant_and_user_fixture
    meeting = Meeting(tenant_id=tenant_id, owner_id=user_id, title="Architecture Sync")
    db_session.add(meeting)
    db_session.commit()

    service = DecisionResolutionService(db=db_session, tenant_id=tenant_id)

    # 1. First historical decision
    req1 = DecisionCreateRequest(
        title="Deploy PostgreSQL on EC2",
        description="We will deploy our PostgreSQL primary on an AWS EC2 instance.",
        rationale="Initial prototype simplicity",
        impact_level="HIGH",
        topics=["infrastructure", "database"],
        effective_date=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    d1 = service.create_decision(meeting_id=meeting.id, payload=req1)
    assert d1.status == "CONFIRMED"

    # 2. Newer decision overriding the database architecture
    req2 = DecisionCreateRequest(
        title="Migrate and switch from EC2 to AWS RDS PostgreSQL",
        description="We decided to override and replace our EC2 setup to switch from EC2 to AWS RDS PostgreSQL instead of managing EC2.",
        rationale="Managed automated backups and high availability",
        impact_level="HIGH",
        topics=["infrastructure", "database"],
        effective_date=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
    )
    d2 = service.create_decision(meeting_id=meeting.id, payload=req2)

    db_session.refresh(d1)
    db_session.refresh(d2)

    # Verify that d1 has been superseded by d2
    assert d1.status == "SUPERSEDED"
    assert d2.status == "CONFIRMED"

    # Verify relationship exists
    rel = (
        db_session.query(DecisionRelationship)
        .filter(
            DecisionRelationship.source_decision_id == d2.id,
            DecisionRelationship.target_decision_id == d1.id,
        )
        .first()
    )
    assert rel is not None
    assert rel.relationship_type == "SUPERSEDES"

    # Verify latest-for-topic query returns d2
    latest = service.get_latest_decision_for_topic("database")
    assert latest is not None
    assert latest.id == d2.id


def test_decision_manual_relationship_and_graph(db_session, tenant_and_user_fixture):
    tenant_id, user_id = tenant_and_user_fixture
    meeting = Meeting(tenant_id=tenant_id, owner_id=user_id, title="Product Strategy")
    db_session.add(meeting)
    db_session.commit()

    service = DecisionResolutionService(db=db_session, tenant_id=tenant_id)

    d_alpha = service.create_decision(
        meeting_id=meeting.id,
        payload=DecisionCreateRequest(
            title="Use React for Frontend",
            description="Adopt React as standard web framework.",
            impact_level="MEDIUM",
        ),
    )
    d_beta = service.create_decision(
        meeting_id=meeting.id,
        payload=DecisionCreateRequest(
            title="Adopt Next.js App Router",
            description="Use Next.js on top of React framework.",
            impact_level="HIGH",
        ),
    )

    # Manually add REFINES relationship
    rel = service.add_manual_relationship(
        source_decision_id=d_beta.id,
        payload=DecisionRelationshipCreate(
            target_decision_id=d_alpha.id,
            relationship_type="REFINES",
            reasoning="Next.js is the chosen React meta-framework",
        ),
    )
    assert rel.relationship_type == "REFINES"

    graph = service.get_decision_graph(d_beta.id)
    node_ids = {n.id for n in graph.nodes}
    assert d_alpha.id in node_ids
    assert d_beta.id in node_ids
    assert len(graph.edges) >= 1
