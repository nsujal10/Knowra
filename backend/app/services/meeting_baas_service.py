"""
Service for deploying and managing cloud bots via Meeting Baas API.
Supports Microsoft Teams, Zoom, and Google Meet.
"""

from typing import Any, Dict, Optional
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

MEETING_BAAS_BASE_URL = "https://api.meetingbaas.com/bots"


class MeetingBaasService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.MEETING_BAAS_API_KEY
        self.headers = {
            "x-meeting-baas-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def deploy_bot(
        self,
        meeting_url: str,
        bot_name: str = "Knowra AI Notetaker",
        webhook_url: Optional[str] = None,
        recording_mode: str = "speaker_view",
        speech_to_text: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Deploys an automated bot into a Microsoft Teams, Zoom, or Google Meet call.
        Returns the bot metadata including `bot_id`.
        """
        target_webhook = webhook_url or settings.MEETING_BAAS_WEBHOOK_URL
        if not self.api_key:
            raise ValueError("MEETING_BAAS_API_KEY is not set in environment or settings.")
        if not target_webhook:
            raise ValueError("MEETING_BAAS_WEBHOOK_URL is not set. A public webhook URL is required.")

        payload: Dict[str, Any] = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "webhook_url": target_webhook,
            "recording_mode": recording_mode,
        }
        if speech_to_text:
            payload["speech_to_text"] = speech_to_text

        logger.info(
            "Deploying Meeting Baas bot",
            meeting_url=meeting_url,
            bot_name=bot_name,
            webhook_url=target_webhook,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                MEETING_BAAS_BASE_URL,
                json=payload,
                headers=self.headers,
                timeout=20.0,
            )
            if response.status_code >= 400:
                logger.error("Meeting Baas deploy failed", status=response.status_code, body=response.text)
                response.raise_for_status()
            
            data = response.json()
            logger.info("Meeting Baas bot deployed successfully", data=data)
            return data

    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Gets current status and metadata of a deployed bot."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEETING_BAAS_BASE_URL}/{bot_id}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def leave_meeting(self, bot_id: str) -> bool:
        """Instructs the bot to exit the meeting room."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{MEETING_BAAS_BASE_URL}/{bot_id}",
                headers=self.headers,
                timeout=10.0,
            )
            return response.status_code in (200, 204)


meeting_baas_service = MeetingBaasService()
