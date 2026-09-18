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

    # 3. Format dialogue context for LLM prompt with batching to respect Groq OTPM limits
    segment_items = [{"seq": s.sequence_number, "text": s.text} for s in segments]

    api_key = getattr(settings, "LLM_API_KEY", "") or os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        log.warning("No LLM API key available; skipping AI speaker resolution")
        return {}

    model = getattr(settings, "LLM_MODEL", "qwen/qwen3.8-27b") or "qwen/qwen3.8-27b"
    resolved_names: Dict[str, str] = {}
    attributions: Dict[str, str] = {}

    # Process first batch to identify speakers and attribute early segments
    first_batch = segment_items[:45]
    prompt_1 = f"""You are an expert conversational AI and meeting analyst.
Given the numbered dialogue transcript below:
1. Identify each speaker's real human name (look for self-introductions like "I'm Sarah", "My name is Mike", "Sarah here", or addresses like "Thanks John").
2. If no personal names are mentioned, identify their clear conversational role (e.g. "Presenter", "Inquirer", "Host", "Attendee", "Customer").
3. Attribute each numbered dialogue turn (by its seq number) to the respective speaker ("Speaker A", "Speaker B", etc.).

Dialogue:
{json.dumps(first_batch)}

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

    try:
        res = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt_1}],
                "response_format": {"type": "json_object"},
                "max_tokens": 600,
                "temperature": 0.0,
            },
            timeout=45.0,
        )
        if res.status_code == 200:
            data = json.loads(res.json()["choices"][0]["message"]["content"])
            resolved_names = data.get("speaker_names", {})
            attributions.update(data.get("attributions", {}))
            log.info("LLM resolved initial speakers & attributions", names=resolved_names, turns=len(attributions))
        else:
            log.error("Groq speaker resolution failed", status=res.status_code, body=res.text)
    except Exception as e:
        log.exception("Error during LLM speaker resolution batch 1", error=str(e))

    # If transcript has subsequent segments, attribute them using identified speakers
    chunk_size = 45
    for offset in range(45, len(segment_items), chunk_size):
        chunk = segment_items[offset : offset + chunk_size]
        speakers_for_prompt = resolved_names if resolved_names else list(speaker_by_label.keys())
        prompt_sub = f"""Given these speakers: {json.dumps(speakers_for_prompt)}
Attribute each numbered dialogue turn (by its seq number) to the most likely speaker.

Dialogue:
{json.dumps(chunk)}

Return a single valid JSON object:
{{
  "attributions": {{
    "{chunk[0]['seq']}": "Speaker A"
  }}
}}
"""
        try:
            res = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt_sub}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 500,
                    "temperature": 0.0,
                },
                timeout=45.0,
            )
            if res.status_code == 200:
                data = json.loads(res.json()["choices"][0]["message"]["content"])
                sub_attrs = data.get("attributions", {})
                attributions.update(sub_attrs)
            else:
                log.warning("Groq sub-batch attribution skipped", status=res.status_code)
        except Exception as e:
            log.warning("Sub-batch attribution error", error=str(e))


    # 4. Apply resolved names to Speaker records (or create new speakers if identified)
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
            # Check if matching existing speaker
            matched_spk = None
            for s in speakers:
                if s.speaker_label.lower() in label.lower() or label.lower() in s.speaker_label.lower():
                    matched_spk = s
                    break
            
            if matched_spk:
                matched_spk.display_name = clean_name
                speaker_by_label[label] = matched_spk
                updated_speakers[str(matched_spk.id)] = clean_name
            else:
                # Dynamically create new speaker for this meeting
                new_spk = Speaker(
                    tenant_id=tenant_id,
                    meeting_id=meeting_id,
                    speaker_label=label,
                    display_name=clean_name,
                )
                db.add(new_spk)
                db.flush()
                speakers.append(new_spk)
                speaker_by_label[label] = new_spk
                updated_speakers[str(new_spk.id)] = clean_name

    # 5. Build lookup map for attribution (supporting both labels & names)
    speaker_map = {}
    for s in speakers:
        if s.speaker_label:
            speaker_map[s.speaker_label.lower()] = s
        if s.display_name:
            speaker_map[s.display_name.lower()] = s

    # 6. Apply segment attributions to transcript segments
    if attributions:
        for s in segments:
            assigned = attributions.get(str(s.sequence_number))
            if not assigned:
                assigned = attributions.get(s.sequence_number)

            matched = None
            if assigned:
                assigned_clean = str(assigned).strip().lower()
                if assigned_clean in speaker_map:
                    matched = speaker_map[assigned_clean]
                else:
                    for k, spk in speaker_map.items():
                        if k in assigned_clean or assigned_clean in k:
                            matched = spk
                            break

            if matched:
                s.speaker_id = matched.id
            elif not s.speaker_id and speakers:
                s.speaker_id = speakers[0].id

    db.commit()
    log.info("Speaker resolution & attribution finished", updated_speakers=updated_speakers)
    return updated_speakers

