"""
Decision Synchronization Service
Ensures all decisions extracted during intelligence runs are materialized
into Phase 17 EnterpriseDecision graph entities with topics and evidence snippets.
"""

from __future__ import annotations

import re
from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.orm import Session

from app.decisions.models import (
    EnterpriseDecision,
    DecisionEvidence,
    DecisionTopic,
    DecisionEvent,
)
from app.decisions.resolver import DecisionResolutionService
from app.intelligence.models import Decision as MeetingDecision
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


def infer_decision_title(description: str) -> str:
    """Generate a concise, punchy title from a decision description."""
    clean = description.strip()
    if len(clean) <= 75:
        return clean
    # Try finding first sentence
    match = re.split(r"[.!?]\s+", clean)
    if match and len(match[0]) <= 85:
        return match[0].rstrip(".")
    # Fallback to first 80 characters without cutting words
    words = clean.split()
    title_words = []
    current_len = 0
    for w in words:
        if current_len + len(w) + 1 > 75:
            break
        title_words.append(w)
        current_len += len(w) + 1
    return " ".join(title_words) + ("..." if len(title_words) < len(words) else "")


def infer_decision_category(text: str) -> str:
    """Infer an enterprise category topic from decision text."""
    lower = text.lower()
    if any(k in lower for k in ["database", "api", "architecture", "ec2", "aws", "rds", "backend", "cache", "vector", "pinecone", "weaviate"]):
        return "ARCHITECTURE"
    if any(k in lower for k in ["security", "leakage", "compliance", "risk", "rbac", "external", "notes", "privacy", "policy"]):
        return "SECURITY"
    if any(k in lower for k in ["app", "ui", "mobile", "frontend", "roadmap", "feature", "pilot", "react native", "integration", "slack", "copilot"]):
        return "PRODUCT"
    if any(k in lower for k in ["release", "production", "deploy", "pipeline", "test", "verification", "run", "transcript", "model"]):
        return "ENGINEERING"
    return "OPERATIONS"


def sync_meeting_decisions_to_enterprise(db: Session, tenant_id: Optional[UUID] = None) -> int:
    """
    Syncs extracted MeetingDecision records into canonical EnterpriseDecision records.
    Returns the count of newly synchronized decisions.
    """
    query = db.query(MeetingDecision)
    if tenant_id:
        query = query.filter(MeetingDecision.tenant_id == tenant_id)
    
    meeting_decisions = query.all()
    synced_count = 0

    for md in meeting_decisions:
        # Check if already exists by id
        existing_by_id = db.query(EnterpriseDecision).filter(EnterpriseDecision.id == md.id).first()
        if existing_by_id:
            continue

        title = infer_decision_title(md.description)
        fingerprint = DecisionResolutionService.compute_fingerprint(
            tenant_id=md.tenant_id,
            meeting_id=md.meeting_id,
            title=title,
        )

        existing_by_fp = db.query(EnterpriseDecision).filter(
            EnterpriseDecision.tenant_id == md.tenant_id,
            EnterpriseDecision.fingerprint == fingerprint,
        ).first()
        if existing_by_fp:
            continue

        category = infer_decision_category(f"{title} {md.description}")

        # Materialize EnterpriseDecision
        enterprise_dec = EnterpriseDecision(
            id=md.id,
            tenant_id=md.tenant_id,
            meeting_id=md.meeting_id,
            intelligence_run_id=md.intelligence_run_id,
            title=title,
            description=md.description,
            rationale=md.rationale,
            status="CONFIRMED",
            impact_level=md.impact_level.upper() if md.impact_level else "MEDIUM",
            decided_by_raw=md.decided_by_raw or "Executive Committee",
            decided_by_user_id=md.decided_by_user_id,
            fingerprint=fingerprint,
            evidence_segment_ids=md.evidence_segment_ids or [],
            created_at=md.created_at,
        )
        db.add(enterprise_dec)
        db.flush()

        # Add topic tag
        db.add(DecisionTopic(
            id=uuid4(),
            tenant_id=md.tenant_id,
            decision_id=enterprise_dec.id,
            topic_name=category.lower(),
            relevance_score=1.0,
            created_at=md.created_at,
        ))

        # Add evidence items
        if md.evidence_segment_ids:
            for raw_seg_id in md.evidence_segment_ids:
                try:
                    seg_uuid = UUID(str(raw_seg_id))
                    seg = db.query(TranscriptSegment).filter(
                        TranscriptSegment.id == seg_uuid,
                    ).first()
                    snippet = seg.text if seg else None
                    db.add(DecisionEvidence(
                        id=uuid4(),
                        tenant_id=md.tenant_id,
                        decision_id=enterprise_dec.id,
                        segment_id=seg_uuid,
                        snippet=snippet,
                        confidence=1.0,
                        created_at=md.created_at,
                    ))
                except Exception:
                    pass

        # Add audit event
        db.add(DecisionEvent(
            id=uuid4(),
            tenant_id=md.tenant_id,
            decision_id=enterprise_dec.id,
            actor_user_id=md.decided_by_user_id,
            event_type="CREATED",
            new_state={"title": title, "status": "CONFIRMED", "origin": "intelligence_extraction"},
            created_at=md.created_at,
        ))

        synced_count += 1

    if synced_count > 0:
        db.commit()
        logger.info("synchronized_meeting_decisions", count=synced_count)

    return synced_count
