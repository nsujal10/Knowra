"""
Phase 21 & 22 – Post-Generation Citation Validator

Validates every chunk_id and segment_id returned by the LLM against the
authorized retrieval set and canonical database records. Drops hallucinated
or unauthorized evidence before returning responses to clients.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.knowledge.models import KnowledgeChunkSegment
from app.knowledge.schemas import SearchResultItem
from app.models.transcript_segment import TranscriptSegment
from app.rag.schemas import RAGCitation


class CitationValidator:
    """
    Guarantees citation integrity through post-generation verification:
      1. Every cited chunk_id must exist in the authorized search results set.
      2. Every cited segment_id must be mapped to that chunk in the canonical junction table.
      3. The segment must belong to the caller's verified tenant_id.
    """

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def validate(
        self,
        raw_citations: List[dict],
        retrieved_results: List[SearchResultItem],
    ) -> List[RAGCitation]:
        """
        Validates raw citations produced by the LLM.
        Returns only verifiable citations anchored in canonical DB records.
        """
        if not raw_citations:
            return []

        # Index retrieved chunks and segment mappings
        retrieved_chunk_ids = {item.chunk_id: item for item in retrieved_results}

        # Build mapping of chunk_id -> dict of segment_id -> CitationSegmentSchema
        retrieved_segment_map = {}
        for item in retrieved_results:
            for seg in item.citations:
                retrieved_segment_map[(item.chunk_id, seg.segment_id)] = (item, seg)

        verified_citations: List[RAGCitation] = []

        for raw in raw_citations:
            try:
                raw_chunk_id = raw.get("chunk_id")
                raw_seg_id = raw.get("segment_id")
                if not raw_chunk_id or not raw_seg_id:
                    continue

                chunk_id = UUID(str(raw_chunk_id))
                segment_id = UUID(str(raw_seg_id))
            except (ValueError, TypeError):
                # Malformed UUID -> Drop hallucination
                continue

            # Check 1: Was this chunk in the authorized retrieval results?
            if chunk_id not in retrieved_chunk_ids:
                continue

            # Check 2: Was this segment actually associated with this chunk in the retrieved set?
            mapping_key = (chunk_id, segment_id)
            if mapping_key in retrieved_segment_map:
                item, seg = retrieved_segment_map[mapping_key]
                quote = str(raw.get("quote") or seg.text).strip()
                verified_citations.append(
                    RAGCitation(
                        chunk_id=chunk_id,
                        segment_id=segment_id,
                        start_seconds=seg.start_seconds,
                        end_seconds=seg.end_seconds,
                        speaker_name=seg.speaker_name,
                        quote=quote,
                        verified=True,
                    )
                )
                continue

            # Check 3: Fallback verification against canonical DB records
            junction = (
                self.db.query(KnowledgeChunkSegment)
                .filter(
                    KnowledgeChunkSegment.chunk_id == chunk_id,
                    KnowledgeChunkSegment.segment_id == segment_id,
                    KnowledgeChunkSegment.tenant_id == self.tenant_id,
                )
                .first()
            )
            if not junction:
                # Segment does not belong to this chunk in tenant -> Drop
                continue

            db_segment = (
                self.db.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.id == segment_id,
                    TranscriptSegment.tenant_id == self.tenant_id,
                )
                .first()
            )
            if not db_segment:
                continue

            speaker_name = (
                (db_segment.speaker.display_name or db_segment.speaker.speaker_label)
                if db_segment.speaker
                else "Unknown"
            )
            quote = str(raw.get("quote") or db_segment.text).strip()

            verified_citations.append(
                RAGCitation(
                    chunk_id=chunk_id,
                    segment_id=segment_id,
                    start_seconds=db_segment.start_seconds,
                    end_seconds=db_segment.end_seconds,
                    speaker_name=speaker_name,
                    quote=quote,
                    verified=True,
                )
            )

        return verified_citations
