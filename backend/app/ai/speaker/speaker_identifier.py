import os
import json
import httpx
import structlog
from uuid import UUID
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment

logger = structlog.get_logger(__name__)


def resolve_speaker_identities(
    db: Session,
    tenant_id: UUID,
    meeting_id: UUID,
) -> Dict[str, str]:
    """
    Analyzes meeting transcript using Groq LLM to:
    1. Identify real speaker names (e.g., 'Sarah', 'Mike', 'Alison Barker') or descriptive roles ('Presenter', 'Inquirer').
    2. Attribute conversation segments to the correct speaker throughout the meeting.
    3. Update Speaker.display_name and TranscriptSegment.speaker_id.
    """
    log = logger.bind(tenant_id=str(tenant_id), meeting_id=str(meeting_id))
    log.info("Starting AI Speaker Name Resolution & Attribution")

    # 1. Fetch transcript and segments
    transcript = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id, Transcript.tenant_id == tenant_id)
        .first()
    )
    if not transcript:
        log.warning("No transcript found for meeting; skipping speaker resolution")
        return {}

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.transcript_id == transcript.id)
        .order_by(TranscriptSegment.sequence_number.asc())
        .all()
    )
    if not segments:
        log.info("Transcript has 0 segments; skipping speaker resolution")
        return {}

    # 2. Fetch existing speakers or initialize
    speakers = (
        db.query(Speaker)
        .filter(Speaker.meeting_id == meeting_id, Speaker.tenant_id == tenant_id)
        .all()
    )

    if not speakers:
        spk_a = Speaker(
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            speaker_label="Speaker A",
            display_name="Speaker A",
        )
        spk_b = Speaker(
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            speaker_label="Speaker B",
            display_name="Speaker B",
        )
        db.add_all([spk_a, spk_b])
        db.flush()
        speakers = [spk_a, spk_b]

    speaker_by_label = {s.speaker_label: s for s in speakers}

    # 3. Format dialogue context for LLM prompt
    segment_items = [{"seq": s.sequence_number, "text": s.text} for s in segments]

    api_key = getattr(settings, "LLM_API_KEY", "") or os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        log.warning("No LLM API key available; skipping AI speaker resolution")
        return {}

    prompt = f"""You are an expert conversational AI and meeting analyst.
Given the numbered dialogue transcript below:
1. Identify each speaker's real human name (look for self-introductions like "I'm Sarah", "My name is Mike", "Sarah here", or addresses like "Thanks John").
2. If no personal names are mentioned, identify their clear conversational role (e.g. "Presenter", "Inquirer", "Host", "Attendee", "Customer").
3. Attribute each numbered dialogue turn (by its seq number) to the respective speaker ("Speaker A", "Speaker B", etc.).

Dialogue:
{json.dumps(segment_items)}

Return a single valid JSON object in this exact format:
{{
  "speaker_names": {{
    "Speaker A": "Real Name or Role",
    "Speaker B": "Real Name or Role"
  }},
  "attributions": {{
    "0": "Speaker A",
    "1": "Speaker B"
  }}
}}
"""

    model = getattr(settings, "LLM_MODEL", "qwen/qwen3.8-27b") or "qwen/qwen3.8-27b"
    resolved_names: Dict[str, str] = {}
    attributions: Dict[str, str] = {}

    try:
        res = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            },
            timeout=45.0,
        )
        if res.status_code == 200:
            parsed = res.json()["choices"][0]["message"]["content"]
            data = json.loads(parsed)
            resolved_names = data.get("speaker_names", {})
            attributions = data.get("attributions", {})
            log.info("LLM resolved speaker names & attributions", names=resolved_names, total_turns=len(attributions))
        else:
            log.error("Groq speaker resolution failed", status=res.status_code, body=res.text)
    except Exception as e:
        log.exception("Error during LLM speaker resolution", error=str(e))

    # 4. Apply resolved names to Speaker records
    updated_speakers = {}
    for label, new_name in resolved_names.items():
        if not new_name or not isinstance(new_name, str):
            continue
        clean_name = new_name.strip()
        if label in speaker_by_label:
            spk = speaker_by_label[label]
            spk.display_name = clean_name
            updated_speakers[str(spk.id)] = clean_name
        else:
            # Match partial label e.g. "Speaker 1" -> "Speaker A"
            for s in speakers:
                if s.speaker_label.lower() in label.lower() or label.lower() in s.speaker_label.lower():
                    s.display_name = clean_name
                    updated_speakers[str(s.id)] = clean_name
                    break

    # 5. Apply segment attributions to transcript segments
    if attributions:
        for s in segments:
            assigned_label = attributions.get(str(s.sequence_number))
            if assigned_label and assigned_label in speaker_by_label:
                s.speaker_id = speaker_by_label[assigned_label].id
            elif assigned_label:
                for label, spk in speaker_by_label.items():
                    if label.lower() in assigned_label.lower() or assigned_label.lower() in label.lower():
                        s.speaker_id = spk.id
                        break

    db.commit()
    log.info("Speaker resolution & attribution finished", updated_speakers=updated_speakers)
    return updated_speakers
