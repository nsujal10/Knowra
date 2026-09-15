"""
Integration Test: Cross-Meeting Timeline Builder (Phase 23)
Verifies that the TimelineBuilder correctly sequences related topics, decisions,
and action items from separate meetings in strict chronological order.
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models.enums import MediaStatus
from app.models.media_asset import MediaAsset
from app.models.meeting import Meeting
from app.models.organization import Organization
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.actions.models import ActionItem
from app.auth.scope import AuthorizedRetrievalScope
from app.decisions.models import EnterpriseDecision
from app.intelligence.cross_meeting.timeline import TimelineBuilder
from app.intelligence.models import Topic


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_cross_meeting_timeline_chronological_sequencing(db_session):
    run_id = str(uuid.uuid4())[:8]

    # 1. Provision Tenant and User
    org = Organization(name=f"Timeline Corp {run_id}", slug=f"timeline-{run_id}")
    db_session.add(org)
    db_session.commit()

    user = User(email=f"pm_{run_id}@timeline.com", password_hash="hash", full_name="Project Manager")
    db_session.add(user)
    db_session.flush()

    # 2. Provision 3 Chronological Meetings spanning Jan, Feb, Mar
    d1 = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    d2 = datetime(2026, 2, 15, 14, 0, tzinfo=timezone.utc)
    d3 = datetime(2026, 3, 20, 16, 0, tzinfo=timezone.utc)

    m1 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 1 - Titan Kickoff", meeting_date=d1)
    m2 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 2 - Titan Benchmarks", meeting_date=d2)
    m3 = Meeting(tenant_id=org.id, owner_id=user.id, title="Sprint 3 - Titan Launch", meeting_date=d3)
    db_session.add_all([m1, m2, m3])
    db_session.flush()

    # Media & Transcripts for segments
    ma1 = MediaAsset(tenant_id=org.id, meeting_id=m1.id, filename="m1.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
    ma2 = MediaAsset(tenant_id=org.id, meeting_id=m2.id, filename="m2.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
    ma3 = MediaAsset(tenant_id=org.id, meeting_id=m3.id, filename="m3.mp4", original_content_type="video/mp4", status=MediaStatus.READY)
    db_session.add_all([ma1, ma2, ma3])
    db_session.flush()

    t1 = Transcript(tenant_id=org.id, meeting_id=m1.id, media_asset_id=ma1.id, language="en", duration_seconds=120.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
    t2 = Transcript(tenant_id=org.id, meeting_id=m2.id, media_asset_id=ma2.id, language="en", duration_seconds=120.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
    t3 = Transcript(tenant_id=org.id, meeting_id=m3.id, media_asset_id=ma3.id, language="en", duration_seconds=120.0, provider_name="faster-whisper", model_name="base", model_version="1.0")
    db_session.add_all([t1, t2, t3])
    db_session.flush()

    seg1 = TranscriptSegment(tenant_id=org.id, transcript_id=t1.id, sequence_number=0, start_seconds=15.0, end_seconds=30.0, text="Project Titan architecture discussion", confidence=0.98)
    seg2 = TranscriptSegment(tenant_id=org.id, transcript_id=t2.id, sequence_number=0, start_seconds=45.0, end_seconds=60.0, text="Benchmarking Project Titan latency", confidence=0.97)
    seg3 = TranscriptSegment(tenant_id=org.id, transcript_id=t3.id, sequence_number=0, start_seconds=5.0, end_seconds=20.0, text="Project Titan go-live approval", confidence=0.99)
    db_session.add_all([seg1, seg2, seg3])
    db_session.flush()

    # 3. Add Cross-Meeting Artifacts:
    from app.intelligence.models import IntelligenceRun
    intel_run = IntelligenceRun(
        tenant_id=org.id,
        meeting_id=m1.id,
        transcript_version_number=1,
        status="COMPLETED",
        prompt_tokens=100,
        completion_tokens=50,
        processing_time_seconds=1.5,
        idempotency_key=f"idem_{run_id}",
    )
    db_session.add(intel_run)
    db_session.flush()

    # Meeting 1: Topic + Decision
    topic1 = Topic(
        tenant_id=org.id,
        meeting_id=m1.id,
        intelligence_run_id=intel_run.id,
        title="Project Titan Kickoff",
        summary="Initial architectural review for Project Titan.",
        start_seconds=15.0,
        end_seconds=30.0,
        evidence_segment_ids=[str(seg1.id)],
    )
    dec1 = EnterpriseDecision(
        tenant_id=org.id, meeting_id=m1.id, title="Adopt PostgreSQL for Project Titan",
        description="Agreed to use PostgreSQL and pgvector for Project Titan.",
        fingerprint=f"fp1_{run_id}", status="CONFIRMED", decided_by_raw="Project Manager",
        evidence_segment_ids=[str(seg1.id)]
    )

    # Meeting 2: Action Item
    action2 = ActionItem(
        tenant_id=org.id,
        meeting_id=m2.id,
        title="Benchmark Project Titan Latency",
        description="Run performance tests on Project Titan before end of week.",
        owner_raw="QA Lead",
        status="OPEN",
        fingerprint_hash=f"fp_act_{run_id}",
    )

    # Meeting 3: Final Launch Decision
    dec3 = EnterpriseDecision(
        tenant_id=org.id, meeting_id=m3.id, title="Approve Project Titan Production Go-Live",
        description="Confirmed Project Titan is ready for enterprise production release.",
        fingerprint=f"fp3_{run_id}", status="CONFIRMED", decided_by_raw="VP Engineering",
        evidence_segment_ids=[str(seg3.id)]
    )

    db_session.add_all([topic1, dec1, action2, dec3])
    db_session.commit()

    # 4. Execute TimelineBuilder
    builder = TimelineBuilder(db=db_session)
    scope = AuthorizedRetrievalScope(
        tenant_id=org.id,
        user_id=user.id,
        role_code="ADMIN",
        permissions={"meetings:read"},
        allowed_meeting_ids=None,
    )

    timeline = builder.build_timeline(scope=scope, entity_or_topic="Project Titan")

    assert timeline.total_events >= 4
    assert timeline.meetings_covered == 3

    # Verify Strict Chronological Ordering
    events = timeline.events
    for i in range(len(events) - 1):
        d_curr = events[i].meeting_date
        d_next = events[i + 1].meeting_date
        assert d_curr <= d_next, f"Event {events[i].title} ({d_curr}) is not before {events[i+1].title} ({d_next})"

    # Verify Evidence Linking
    titan_topic = next(e for e in events if e.event_type == "TOPIC")
    assert str(seg1.id) in [str(x) for x in titan_topic.evidence_segment_ids]
    assert titan_topic.meeting_title == "Sprint 1 - Titan Kickoff"
