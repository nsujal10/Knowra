"""
API endpoints for Meeting Baas Bot deployment and webhook processing.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
import structlog

from app.core.config import settings
from app.services.meeting_baas_service import meeting_baas_service

logger = structlog.get_logger(__name__)
router = APIRouter()


class DeployBotRequest(BaseModel):
    meeting_url: str
    bot_name: Optional[str] = "Knowra AI Notetaker"
    webhook_url: Optional[str] = None


@router.get("/webhook", summary="Webhook health verification")
async def webhook_health():
    """Simple verification endpoint when accessed via browser or GET request."""
    return {
        "status": "active",
        "service": "Knowra Meeting Baas Webhook Receiver",
        "configured_webhook_url": settings.MEETING_BAAS_WEBHOOK_URL or "Not set in .env",
    }


@router.post("/webhook", summary="Inbound webhook from Meeting Baas")
async def receive_meeting_baas_webhook(request: Request) -> Dict[str, Any]:
    """
    Receives live transcripts and bot lifecycle events from Meeting Baas.
    Meeting Baas sends:
      - bot.status_change: joining, in_call, completed, failed
      - transcript: speaker, text, words, timestamps
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    event = body.get("event") or body.get("type") or "unknown"
    data = body.get("data") or body

    logger.info("Received Meeting Baas webhook event", event=event, keys=list(data.keys()) if isinstance(data, dict) else [])

    # Handle transcription event
    if "transcript" in event or "speech" in event or "words" in data or "speaker" in data:
        speaker = data.get("speaker") or data.get("speaker_name") or "Attendee"
        text = data.get("text") or data.get("transcript") or ""
        logger.info("Meeting Baas live speech captured", speaker=speaker, text=text)

    # Handle bot lifecycle event
    elif "status" in event or "bot" in event:
        bot_id = data.get("bot_id")
        status_val = data.get("status") or data.get("new_status")
        logger.info("Meeting Baas bot status changed", bot_id=bot_id, status=status_val)

    return {"status": "ok", "event_received": event}


@router.post("/deploy", summary="Deploy bot into a live meeting")
async def deploy_bot(req: DeployBotRequest) -> Dict[str, Any]:
    """
    Triggers Meeting Baas to send a bot to the specified meeting URL.
    """
    if not req.meeting_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="meeting_url is required."
        )

    try:
        result = await meeting_baas_service.deploy_bot(
            meeting_url=req.meeting_url,
            bot_name=req.bot_name or "Knowra AI Notetaker",
            webhook_url=req.webhook_url,
        )
        return {"status": "success", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to deploy bot", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Meeting Baas: {str(e)}"
        )
