from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from uuid import UUID
from typing import List

from app.core.tenant_db import get_tenant_db
from app.security.tenant import TenantContext, get_tenant_context
from app.models.meeting import Meeting
from app.models.media_asset import MediaAsset
from app.models.processing_job import ProcessingJob
from app.models.speaker import Speaker
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.schemas.diarization import (
    DiarizationJobResponse,
    DiarizationStatusResponse,
    SpeakerResponse,
    SpeakerUpdateRequest,
    DiarizedTranscriptResponse,
    DiarizedSegmentSchema,
    DiarizedWordSchema,
)
from app.services.diarization_service import DiarizationService
from app.workers.diarization_worker import execute_diarization_task

router = APIRouter()


@router.post(
    "/meetings/{meeting_id}/diarization",
    response_model=DiarizationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_diarization(
    meeting_id: UUID,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.tenant_id == tenant_ctx.tenant_id)
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    media = (
        db.query(MediaAsset)
        .filter(MediaAsset.meeting_id == meeting_id, MediaAsset.tenant_id == tenant_ctx.tenant_id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found for meeting")

    job = ProcessingJob(
        tenant_id=tenant_ctx.tenant_id,
        media_asset_id=media.id,
        task_name="DIARIZATION",
        status="PENDING",
    )
    db.add(job)
    db.commit()

    execute_diarization_task.delay(str(job.id), str(tenant_ctx.tenant_id), str(media.id))
    return DiarizationJobResponse(
        message="Speaker diarization job queued",
        job_id=str(job.id),
    )


@router.get(
    "/meetings/{meeting_id}/diarization",
    response_model=DiarizationStatusResponse,
)
def get_diarization_status(
    meeting_id: UUID,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    media = (
        db.query(MediaAsset)
        .filter(MediaAsset.meeting_id == meeting_id, MediaAsset.tenant_id == tenant_ctx.tenant_id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    job = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.media_asset_id == media.id,
            ProcessingJob.task_name == "DIARIZATION",
            ProcessingJob.tenant_id == tenant_ctx.tenant_id,
        )
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="No diarization jobs found")

    return DiarizationStatusResponse(
        job_id=str(job.id),
        status=job.status,
        metadata=job.metadata_json,
    )


@router.get(
    "/meetings/{meeting_id}/speakers",
    response_model=List[SpeakerResponse],
)
def get_meeting_speakers(
    meeting_id: UUID,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    service = DiarizationService(db, tenant_ctx.tenant_id)
    speakers = service.get_speakers_for_meeting(meeting_id)
    return [
        SpeakerResponse(
            id=s.id,
            meeting_id=s.meeting_id,
            speaker_label=s.speaker_label,
            display_name=s.display_name,
            user_id=s.user_id,
        )
        for s in speakers
    ]


@router.patch(
    "/speakers/{speaker_id}",
    response_model=SpeakerResponse,
)
def update_speaker(
    speaker_id: UUID,
    req: SpeakerUpdateRequest,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    service = DiarizationService(db, tenant_ctx.tenant_id)
    updated = service.update_speaker(
        speaker_id=speaker_id,
        display_name=req.display_name,
        user_id=req.user_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Speaker not found")

    return SpeakerResponse(
        id=updated.id,
        meeting_id=updated.meeting_id,
        speaker_label=updated.speaker_label,
        display_name=updated.display_name,
        user_id=updated.user_id,
    )


@router.get(
    "/meetings/{meeting_id}/transcript/diarized",
    response_model=DiarizedTranscriptResponse,
)
def get_diarized_transcript(
    meeting_id: UUID,
    db: Session = Depends(get_tenant_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    transcript = (
        db.query(Transcript)
        .options(
            selectinload(Transcript.segments).selectinload(TranscriptSegment.words),
            selectinload(Transcript.segments).selectinload(TranscriptSegment.speaker),
        )
        .filter(
            Transcript.meeting_id == meeting_id,
            Transcript.tenant_id == tenant_ctx.tenant_id,
        )
        .first()
    )

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    service = DiarizationService(db, tenant_ctx.tenant_id)
    speakers = service.get_speakers_for_meeting(meeting_id)
    speakers_schema = [
        SpeakerResponse(
            id=s.id,
            meeting_id=s.meeting_id,
            speaker_label=s.speaker_label,
            display_name=s.display_name,
            user_id=s.user_id,
        )
        for s in speakers
    ]

    segments_schema = []
    for seg in transcript.segments:
        words_schema = [
            DiarizedWordSchema(
                start=w.start_seconds,
                end=w.end_seconds,
                text=w.text,
                confidence=w.confidence,
            )
            for w in seg.words
        ]
        segments_schema.append(
            DiarizedSegmentSchema(
                id=seg.id,
                sequence_number=seg.sequence_number,
                start=seg.start_seconds,
                end=seg.end_seconds,
                text=seg.text,
                confidence=seg.confidence,
                speaker_id=seg.speaker_id,
                speaker_label=seg.speaker.speaker_label if seg.speaker else None,
                speaker_name=seg.speaker.display_name if seg.speaker else None,
                alignment_confidence=seg.alignment_confidence,
                alignment_status=seg.alignment_status,
                words=words_schema,
            )
        )

    return DiarizedTranscriptResponse(
        id=transcript.id,
        meeting_id=transcript.meeting_id,
        language=transcript.language,
        duration=transcript.duration_seconds,
        segments=segments_schema,
        speakers=speakers_schema,
    )
