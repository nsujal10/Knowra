from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from uuid import UUID

from app.core.tenant_db import get_tenant_db
from app.security.tenant import TenantContext, get_tenant_context
from app.models.meeting import Meeting
from app.models.media_asset import MediaAsset
from app.models.processing_job import ProcessingJob
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.transcript_word import TranscriptWord
from app.schemas.transcription import TranscriptResponse, TranscriptSegmentSchema, TranscriptWordSchema
from app.workers.transcription_worker import execute_transcription_task

router = APIRouter()

@router.post("/meetings/{meeting_id}/transcription", status_code=status.HTTP_202_ACCEPTED)
def queue_transcription(meeting_id: UUID, db: Session = Depends(get_tenant_db), tenant_ctx: TenantContext = Depends(get_tenant_context)):
    media = db.query(MediaAsset).filter(MediaAsset.meeting_id == meeting_id, MediaAsset.tenant_id == tenant_ctx.tenant_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found for meeting")
        
    job = ProcessingJob(
        tenant_id=tenant_ctx.tenant_id,
        media_asset_id=media.id,
        task_name="TRANSCRIPTION",
        status="PENDING"
    )
    db.add(job)
    db.commit()
    
    execute_transcription_task.delay(str(job.id), str(tenant_ctx.tenant_id), str(media.id))
    return {"message": "Transcription job queued", "job_id": str(job.id)}

@router.get("/meetings/{meeting_id}/transcription")
def get_transcription_status(meeting_id: UUID, db: Session = Depends(get_tenant_db), tenant_ctx: TenantContext = Depends(get_tenant_context)):
    media = db.query(MediaAsset).filter(MediaAsset.meeting_id == meeting_id, MediaAsset.tenant_id == tenant_ctx.tenant_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    job = db.query(ProcessingJob).filter(
        ProcessingJob.media_asset_id == media.id, 
        ProcessingJob.task_name == "TRANSCRIPTION",
        ProcessingJob.tenant_id == tenant_ctx.tenant_id
    ).order_by(ProcessingJob.created_at.desc()).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="No transcription jobs found")
        
    return {"job_id": str(job.id), "status": job.status, "metadata": job.metadata_json}

@router.get("/meetings/{meeting_id}/transcript", response_model=TranscriptResponse)
def get_transcript(meeting_id: UUID, db: Session = Depends(get_tenant_db), tenant_ctx: TenantContext = Depends(get_tenant_context)):
    transcript = db.query(Transcript).options(
        selectinload(Transcript.segments).selectinload(TranscriptSegment.words)
    ).filter(
        Transcript.meeting_id == meeting_id,
        Transcript.tenant_id == tenant_ctx.tenant_id
    ).first()
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
        
    segments_schema = []
    for seg in transcript.segments:
        words_schema = [TranscriptWordSchema(start=w.start_seconds, end=w.end_seconds, text=w.text, confidence=w.confidence) for w in seg.words]
        segments_schema.append(
            TranscriptSegmentSchema(
                start=seg.start_seconds, 
                end=seg.end_seconds, 
                text=seg.text, 
                confidence=seg.confidence,
                words=words_schema
            )
        )
        
    return TranscriptResponse(
        id=transcript.id,
        meeting_id=transcript.meeting_id,
        language=transcript.language,
        duration=transcript.duration_seconds,
        segments=segments_schema
    )
