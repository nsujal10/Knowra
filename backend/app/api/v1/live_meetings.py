"""
Live Meeting Streaming API Endpoints

Provides:
- POST      /meetings/live/start               - Start or initialize a live meeting
- WebSocket /meetings/{meeting_id}/live-stream      - Ingest multi-channel audio & speaker hints
- WebSocket /meetings/{meeting_id}/live-transcript  - Broadcast real-time transcript & speakers
- POST      /meetings/{meeting_id}/live/end         - End meeting & finalize canonical transcript
- GET       /meetings/{meeting_id}/live/status      - Get live meeting status & channel stats
"""

import base64
import json
import uuid
from typing import Optional
import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.tenant import TenantContext, get_tenant_context
from app.services.live_meeting_service import LiveMeetingManager
from app.models.meeting import Meeting
from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()


class StartLiveMeetingRequest(BaseModel):
    title: Optional[str] = "Live Meeting"
    hostName: Optional[str] = None
    attendees: Optional[str] = None
    language: Optional[str] = "hi"


class StartLiveMeetingResponse(BaseModel):
    meetingId: str
    status: str
    hostSpeakerLabel: str
    liveStreamWsUrl: str
    liveTranscriptWsUrl: str


class EndLiveMeetingResponse(BaseModel):
    meetingId: str
    status: str
    message: str


@router.post(
    "/live/start",
    response_model=StartLiveMeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize a live meeting session",
)
async def start_live_meeting(
    payload: StartLiveMeetingRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    meeting_id = uuid.uuid4()
    manager = LiveMeetingManager.get_instance()

    # Resolve host name: prefer explicit payload, otherwise look up user's real full_name
    resolved_host = payload.hostName
    if not resolved_host or resolved_host in ("You (Host)", "Host", ""):
        user = db.query(User).filter(User.id == tenant_ctx.user_id).first()
        if user and user.full_name:
            resolved_host = user.full_name
        else:
            resolved_host = "Sujal Nage"

    meeting = Meeting(
        id=meeting_id,
        tenant_id=tenant_ctx.tenant_id,
        owner_id=tenant_ctx.user_id,
        title=payload.title or "Live Meeting",
        status="IN_PROGRESS",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    await manager.start_session(
        db=db,
        meeting_id=meeting_id,
        tenant_id=tenant_ctx.tenant_id,
        owner_id=tenant_ctx.user_id,
        host_name=resolved_host,
        remote_name=payload.attendees or "Remote Attendee",
        language=payload.language or "hi",
    )

    return StartLiveMeetingResponse(
        meetingId=str(meeting_id),
        status="IN_PROGRESS",
        hostSpeakerLabel="SPEAKER_HOST",
        liveStreamWsUrl=f"/api/v1/meetings/{meeting_id}/live-stream",
        liveTranscriptWsUrl=f"/api/v1/meetings/{meeting_id}/live-transcript",
    )


@router.post(
    "/{meeting_id}/live/end",
    response_model=EndLiveMeetingResponse,
    summary="End live meeting and finalize canonical transcript",
)
async def end_live_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    from app.api.v1.intelligence import resolve_meeting
    meeting = resolve_meeting(meeting_id, tenant_ctx.tenant_id, db)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    manager = LiveMeetingManager.get_instance()
    await manager.end_session(meeting.id)

    return EndLiveMeetingResponse(
        meetingId=str(meeting.id),
        status="COMPLETED",
        message="Live meeting ended and canonical transcript finalized.",
    )


@router.get(
    "/{meeting_id}/live/status",
    summary="Get active live meeting status",
)
async def get_live_status(
    meeting_id: str,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    from app.api.v1.intelligence import resolve_meeting
    meeting = resolve_meeting(meeting_id, tenant_ctx.tenant_id, db)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    manager = LiveMeetingManager.get_instance()
    session = manager.get_session(meeting.id)

    if not session or not session.is_active:
        return {
            "meetingId": str(meeting.id),
            "isActive": False,
            "status": meeting.status,
            "channels": {},
        }

    channels_info = {
        ch_id: {
            "channelId": ch_id,
            "speakerLabel": buf.speaker_label,
            "displayName": buf.display_name,
            "lastActive": buf.last_speech_time,
        }
        for ch_id, buf in session.channels.items()
    }

    return {
        "meetingId": str(meeting.id),
        "isActive": True,
        "status": "IN_PROGRESS",
        "elapsedSeconds": round(time.time() - session.start_wall_time, 2) if hasattr(session, "start_wall_time") else 0,
        "channels": channels_info,
    }


# -----------------------------------------------------------------------------
# WebSocket: Ingest Audio Stream
# -----------------------------------------------------------------------------

@router.websocket("/{meeting_id}/live-stream")
async def websocket_live_stream(websocket: WebSocket, meeting_id: str):
    """
    Ingests live multi-track audio chunks from companion app or browser.
    Expected JSON message:
    {
      "channel": 1,                     # 1 = Host Mic, 2+ = Remote Meeting Audio
      "speaker_hint": "Alex Connor",     # Optional active speaker name
      "text_hint": "Hello everyone",     # Optional client-side transcription
      "audio_base64": "..."             # Raw PCM / WAV / WebM bytes
    }
    """
    await websocket.accept()
    manager = LiveMeetingManager.get_instance()

    try:
        meeting_uuid = uuid.UUID(meeting_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Check session or auto-initialize with DB
    session = manager.get_session(meeting_uuid)
    if not session:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
            if meeting:
                session = await manager.start_session(
                    db=db,
                    meeting_id=meeting.id,
                    tenant_id=meeting.tenant_id,
                    owner_id=meeting.owner_id,
                )
        finally:
            db.close()

    if not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.register_stream_client(meeting_uuid, websocket)
    logger.info("Audio ingestion stream connected", meeting_id=meeting_id)

    try:
        while True:
            # Accepts either text (JSON with base64 audio/hints) or binary PCM frames
            data = await websocket.receive()
            if "text" in data:
                try:
                    msg = json.loads(data["text"])
                    channel = int(msg.get("channel", 1))
                    speaker_hint = msg.get("speaker_hint")
                    text_hint = msg.get("text_hint")
                    roster_hint = msg.get("roster_hint")
                    audio_b64 = msg.get("audio_base64")
                    audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""

                    await manager.ingest_audio_chunk(
                        meeting_id=meeting_uuid,
                        channel_id=channel,
                        audio_bytes=audio_bytes,
                        speaker_hint=speaker_hint,
                        text_hint=text_hint,
                        roster_hint=roster_hint,
                    )
                except Exception as e:
                    logger.debug("Error parsing live audio message", error=str(e))
            elif "bytes" in data:
                # Default binary stream is Channel 1 (host)
                await manager.ingest_audio_chunk(
                    meeting_id=meeting_uuid,
                    channel_id=1,
                    audio_bytes=data["bytes"],
                )
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Audio stream disconnected", meeting_id=meeting_id)
    finally:
        await manager.unregister_stream_client(meeting_uuid, websocket)


# -----------------------------------------------------------------------------
# WebSocket: Live Transcript Broadcast
# -----------------------------------------------------------------------------

@router.websocket("/{meeting_id}/live-transcript")
async def websocket_live_transcript(websocket: WebSocket, meeting_id: str):
    """
    Broadcasts real-time transcript segments to frontend UI clients.
    """
    await websocket.accept()
    manager = LiveMeetingManager.get_instance()

    try:
        meeting_uuid = uuid.UUID(meeting_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.register_subscriber(meeting_uuid, websocket)
    logger.info("Transcript subscriber connected", meeting_id=meeting_id)

    try:
        while True:
            # Keep-alive ping / wait for client
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        logger.info("Transcript subscriber disconnected", meeting_id=meeting_id)
    finally:
        await manager.unregister_subscriber(meeting_uuid, websocket)
