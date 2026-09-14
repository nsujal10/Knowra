"""
Phase 18 – Semantic Conversation Chunker

Chunks transcripts based on conversational structure, speaker dialogue turns,
and semantic topic boundaries rather than arbitrary token splits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from app.models.transcript_segment import TranscriptSegment


@dataclass
class RawChunk:
    content: str
    token_count: int
    start_seconds: float
    end_seconds: float
    speaker_names: List[str]
    segment_ids: List[UUID]
    primary_topic: Optional[str] = None


class SemanticChunker:
    """
    Groups contiguous conversation turns into semantically cohesive passages.
    Preserves:
      - Speaker turn continuity
      - Exact segment IDs for downstream citation resolution
      - Start & end timestamps for video timeline seeking
    """

    def __init__(
        self,
        target_token_min: int = 40,
        target_token_max: int = 250,
        pause_threshold_seconds: float = 8.0,
    ) -> None:
        self.target_token_min = target_token_min
        self.target_token_max = target_token_max
        self.pause_threshold_seconds = pause_threshold_seconds

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text.split()))

    def chunk_segments(
        self,
        segments: List[TranscriptSegment],
        topic_bounds: Optional[List[dict]] = None,
    ) -> List[RawChunk]:
        """
        Transforms a sequence of canonical transcript segments into semantic chunks.
        respecting speaker transitions, pauses (>8s), and topic boundaries.
        """
        if not segments:
            return []

        chunks: List[RawChunk] = []

        current_lines: List[str] = []
        current_segment_ids: List[UUID] = []
        current_speakers: List[str] = []
        current_start: float = segments[0].start_seconds
        current_end: float = segments[0].end_seconds
        current_tokens: int = 0
        current_topic: Optional[str] = None

        for idx, seg in enumerate(segments):
            speaker_name = (
                (seg.speaker.display_name or seg.speaker.speaker_label)
                if seg.speaker
                else "Unknown Speaker"
            )
            line = f"{speaker_name}: {seg.text}"
            tokens = self.estimate_tokens(line)

            # Check for topic tag match if topic_bounds provided
            matching_topic = None
            if topic_bounds:
                for t in topic_bounds:
                    if t.get("start_seconds", 0) <= seg.start_seconds <= t.get("end_seconds", 999999):
                        matching_topic = t.get("title")
                        break

            # Boundary triggers:
            # 1. Topic boundary change
            topic_changed = current_topic and matching_topic and matching_topic != current_topic
            # 2. Large conversation pause (>pause_threshold_seconds)
            time_gap = seg.start_seconds - current_end
            is_significant_pause = time_gap >= self.pause_threshold_seconds and current_tokens >= self.target_token_min
            # 3. Target token maximum exceeded
            is_max_tokens = (current_tokens + tokens) > self.target_token_max and current_tokens >= self.target_token_min

            if (topic_changed or is_significant_pause or is_max_tokens) and current_lines:
                # Flush current chunk
                content = "\n".join(current_lines)
                chunks.append(
                    RawChunk(
                        content=content,
                        token_count=current_tokens,
                        start_seconds=current_start,
                        end_seconds=current_end,
                        speaker_names=list(dict.fromkeys(current_speakers)),
                        segment_ids=list(current_segment_ids),
                        primary_topic=current_topic,
                    )
                )
                current_lines = []
                current_segment_ids = []
                current_speakers = []
                current_start = seg.start_seconds
                current_tokens = 0

            if not current_lines:
                current_start = seg.start_seconds
                current_topic = matching_topic

            current_lines.append(line)
            current_segment_ids.append(seg.id)
            current_speakers.append(speaker_name)
            current_end = seg.end_seconds
            current_tokens += tokens

        # Flush any remaining lines
        if current_lines:
            content = "\n".join(current_lines)
            chunks.append(
                RawChunk(
                    content=content,
                    token_count=current_tokens,
                    start_seconds=current_start,
                    end_seconds=current_end,
                    speaker_names=list(dict.fromkeys(current_speakers)),
                    segment_ids=list(current_segment_ids),
                    primary_topic=current_topic,
                )
            )

        return chunks
