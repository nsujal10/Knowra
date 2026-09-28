"""
Meeting Title Auto-Generation Service

Intelligently generates crisp, professional, context-aware meeting titles (3-7 words)
from conversation transcripts using Groq LLM with robust heuristics fallbacks.
"""

from __future__ import annotations

import os
import re
from typing import Optional
from uuid import UUID

import httpx
import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)

GENERIC_TITLE_PATTERNS = [
    r"^live\s+sync\b",
    r"^live\s+meeting\b",
    r"^untitled\b",
    r"^new\s+meeting\b",
    r"^meeting\s*[•\-]\s*",
    r"^video\b",
    r"^audio\b",
    r"^recording\b",
    r"^zoom_\d+",
    r"^teams_recording",
    r"^screen_recording",
]

AUDIO_VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4a", ".wav", ".mp3", ".webm",
    ".mkv", ".aac", ".flac", ".ogg", ".wma", ".avi",
}


def is_generic_title(title: Optional[str]) -> bool:
    """
    Determines if a meeting title is a generic default/placeholder or raw filename,
    meaning the user did NOT enter a custom descriptive title.
    """
    if not title:
        return True
    t = title.strip()
    if not t or len(t) < 3:
        return True

    tl = t.lower()
    if tl in (
        "live meeting", "live sync", "untitled meeting", "new meeting",
        "meeting", "uploaded meeting", "video", "audio", "recording",
    ):
        return True

    # Check file extensions (e.g., 'meeting_audio.mp4', 'recording_1.wav')
    root, ext = os.path.splitext(tl)
    if ext in AUDIO_VIDEO_EXTENSIONS:
        return True

    # Check regex patterns (e.g. 'Live Sync • 28 Sept', 'Meeting - 2026-09-28')
    for pat in GENERIC_TITLE_PATTERNS:
        if re.search(pat, tl):
            return True

    return False


def clean_generated_title(raw_title: str) -> str:
    """Sanitizes LLM title output: removes markdown, quotes, trailing dots, and limits length."""
    if not raw_title:
        return ""
    t = raw_title.strip()
    # Strip markdown headers or formatting
    t = re.sub(r"^[#*\-_`\s]+", "", t)
    t = re.sub(r"[#*\-_`\s]+$", "", t)
    # Strip quotes
    t = t.strip("\"'“”‘’")
    # Strip common LLM prefixes
    prefixes = [
        "title:", "meeting title:", "suggested title:", "proposed title:",
        "here is a title:", "here's a title:", "generated title:",
    ]
    for p in prefixes:
        if t.lower().startswith(p):
            t = t[len(p):].strip().strip("\"'“”‘’")
    # Strip trailing punctuation
    t = t.rstrip(".,!?:;")
    # Ensure title length between 5 and 90 chars
    words = t.split()
    if len(words) > 9:
        t = " ".join(words[:8])
    return t[:80].strip()


def generate_title_from_text(transcript_text: str) -> Optional[str]:
    """
    Calls LLM (Groq / OpenAI compatible) to summarize dialogue into a 3-6 word professional title.
    Works for English, Hindi, and Hinglish dialogue.
    """
    if not transcript_text or len(transcript_text.strip()) < 15:
        return None

    api_key = settings.LLM_API_KEY or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
    model = settings.LLM_MODEL or os.getenv("LLM_MODEL") or "qwen/qwen3.8-27b"

    # Truncate transcript to first ~2,500 characters (sufficient for meeting topic)
    sample_text = transcript_text.strip()[:2500]

    prompt = (
        "You are an expert AI meeting editor. Based on the following meeting transcript, "
        "generate a concise, professional, and descriptive meeting title (3 to 6 words) in English.\n"
        "STRICT RULES:\n"
        "1. Output ONLY the title itself, with no quotation marks, no preamble, and no markdown.\n"
        "2. The title should reflect the core subject or business goal discussed.\n"
        "3. If discussion is in Hindi, Hinglish, or mixed, output the title in professional English.\n"
        "4. Examples of good titles: 'Architecture Review & Deployment Sync', 'Database Migration Planning', "
        "'Live Transcription Feature Demo'.\n\n"
        f"Transcript:\n{sample_text}"
    )

    if api_key:
        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 40,
                },
                timeout=8.0,
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                cleaned = clean_generated_title(raw)
                if cleaned and len(cleaned.split()) >= 2:
                    return cleaned
        except Exception as e:
            logger.debug("LLM title generation failed, falling back to heuristics", error=str(e))

    # Fast heuristic fallback if LLM is unavailable:
    # Look for common meeting keywords in transcript
    keywords = [
        "architecture", "migration", "deployment", "database", "sprint planning",
        "roadmap", "sync", "demo", "status update", "backend", "frontend",
        "api latency", "onboarding", "testing", "release",
    ]
    matched = [k.title() for k in keywords if k in transcript_text.lower()]
    if matched:
        return f"{' & '.join(matched[:2])} Sync"

    return None


class MeetingTitleService:
    @staticmethod
    def auto_title_meeting(
        db: Session,
        meeting_id: UUID,
        force: bool = False,
    ) -> Optional[str]:
        """
        Auto-generates and updates the meeting title if not custom-entered by user,
        or if force is True.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return None

        # Check if title was already customized by user
        if not force and not is_generic_title(meeting.title):
            logger.info("Skipping auto-title: meeting has custom user title", meeting_id=str(meeting_id), title=meeting.title)
            return meeting.title

        # Fetch canonical transcript segments
        segments = (
            db.query(TranscriptSegment)
            .join(Transcript, TranscriptSegment.transcript_id == Transcript.id)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(TranscriptSegment.start_seconds.asc())
            .limit(60)
            .all()
        )

        if not segments:
            logger.debug("No transcript segments found to generate title", meeting_id=str(meeting_id))
            return None

        dialogue = " ".join([s.text for s in segments if s.text and len(s.text.strip()) > 1])
        if not dialogue or len(dialogue.split()) < 4:
            return None

        new_title = generate_title_from_text(dialogue)
        if new_title and new_title.lower() != meeting.title.lower():
            old_title = meeting.title
            meeting.title = new_title
            db.commit()
            db.refresh(meeting)
            logger.info(
                "Auto-generated meeting title successfully",
                meeting_id=str(meeting_id),
                old_title=old_title,
                new_title=new_title,
            )
            return new_title

        return meeting.title

    @staticmethod
    def backfill_all_generic_titles(db: Session, tenant_id: Optional[UUID] = None) -> dict:
        """
        Backfills intelligent titles for all historical meetings that currently have
        generic placeholder titles (e.g. 'Live Sync • 28 Sept').
        """
        query = db.query(Meeting)
        if tenant_id:
            query = query.filter(Meeting.tenant_id == tenant_id)
        meetings = query.order_by(Meeting.created_at.desc()).all()

        updated_count = 0
        skipped_count = 0
        details = []

        for m in meetings:
            if is_generic_title(m.title):
                old = m.title
                new_t = MeetingTitleService.auto_title_meeting(db, m.id, force=True)
                if new_t and new_t != old:
                    updated_count += 1
                    details.append({"meeting_id": str(m.id), "old_title": old, "new_title": new_t})
                else:
                    skipped_count += 1
            else:
                skipped_count += 1

        logger.info("Completed generic meeting title backfill", updated=updated_count, skipped=skipped_count)
        return {
            "total_scanned": len(meetings),
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "updated_meetings": details,
        }
