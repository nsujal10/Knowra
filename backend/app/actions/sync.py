"""
Action Items Synchronization Service
Ensures verbal commitments and action items extracted across intelligence runs
are materialized into canonical ActionItem records with evidence anchors.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.orm import Session

from app.actions.models import ActionItem, ActionItemEvidence
from app.actions.service import ActionItemService
from app.intelligence.models import Commitment
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


def sync_commitments_to_action_items(db: Session, tenant_id: Optional[UUID] = None) -> int:
    """
    Syncs verbal commitments extracted by meeting intelligence into trackable ActionItem records.
    """
    query = db.query(Commitment)
    if tenant_id:
        query = query.filter(Commitment.tenant_id == tenant_id)

    commitments = query.all()
    synced_count = 0

    for c in commitments:
        fp = ActionItemService.compute_fingerprint(
            tenant_id=c.tenant_id,
            meeting_id=c.meeting_id,
            title=c.statement,
        )

        existing = db.query(ActionItem).filter(
            ActionItem.tenant_id == c.tenant_id,
            (ActionItem.fingerprint_hash == fp) | (ActionItem.id == c.id),
        ).first()

        if existing:
            continue

        item = ActionItem(
            id=c.id,
            tenant_id=c.tenant_id,
            meeting_id=c.meeting_id,
            intelligence_run_id=c.intelligence_run_id,
            title=c.statement,
            description=None,
            status="OPEN",
            priority="MEDIUM",
            owner_raw=c.made_by_raw or "Team",
            fingerprint_hash=fp,
            is_confirmed=True,
            created_at=c.created_at,
        )
        db.add(item)
        db.flush()

        if c.evidence_segment_ids:
            for raw_seg_id in c.evidence_segment_ids:
                try:
                    seg_uuid = UUID(str(raw_seg_id))
                    seg = db.query(TranscriptSegment).filter(
                        TranscriptSegment.id == seg_uuid,
                    ).first()
                    snippet = seg.text if seg else None
                    db.add(ActionItemEvidence(
                        id=uuid4(),
                        tenant_id=c.tenant_id,
                        action_item_id=item.id,
                        segment_id=seg_uuid,
                        snippet=snippet,
                        created_at=c.created_at,
                    ))
                except Exception:
                    pass

        synced_count += 1

    if synced_count > 0:
        db.commit()
        logger.info("synchronized_commitments_to_action_items", count=synced_count)

    return synced_count
