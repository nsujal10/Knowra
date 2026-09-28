import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.meeting_baas_service import MeetingBaasService
from scripts.desktop_meeting_companion import TeamsLiveAttendeeTracker


@pytest.mark.anyio
async def test_meeting_baas_service_deploy_success():
    service = MeetingBaasService(api_key="fake-test-key")
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "bot_id": "test-bot-12345",
        "status": "joining",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response) as mock_post:
        result = await service.deploy_bot(
            meeting_url="https://teams.microsoft.com/l/meetup-join/19%3atest%40thread.v2/0",
            bot_name="Knowra AI Notetaker",
            webhook_url="https://example.com/webhook",
        )
        assert result["bot_id"] == "test-bot-12345"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["x-meeting-baas-api-key"] == "fake-test-key"
        assert kwargs["json"]["meeting_url"] == "https://teams.microsoft.com/l/meetup-join/19%3atest%40thread.v2/0"


@pytest.mark.anyio
async def test_meeting_baas_service_missing_key():
    with patch("app.services.meeting_baas_service.settings.MEETING_BAAS_API_KEY", ""):
        service = MeetingBaasService()
        with pytest.raises(ValueError, match="MEETING_BAAS_API_KEY is not set"):
            await service.deploy_bot("https://teams.microsoft.com/test", webhook_url="https://example.com/webhook")


def test_teams_url_extractor_logic():
    tracker = TeamsLiveAttendeeTracker()
    fake_data = b'something "meetingJoinUrl":"https://teams.microsoft.com/l/meetup-join/19%3atest123%40thread.v2/0?context=%7b%22Tid%22%3a%22abc%22%7d" something'

    with patch("glob.glob", return_value=["dummy.log"]):
        with patch("os.path.getmtime", return_value=12345):
            with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=fake_data)))))):
                url = tracker.extract_active_teams_meeting_url()
                assert url is not None
                assert "teams.microsoft.com/l/meetup-join" in url
