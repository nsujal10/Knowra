from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.endpoints.chat import router as meeting_chat_router
from app.api.v1.media import router as media_router
from app.api.v1.transcription import router as transcription_router
from app.api.v1.diarization import router as diarization_router
from app.api.v1.transcripts import router as transcripts_router
from app.api.v1.speaker_identity import router as speaker_identity_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.actions import router as actions_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.search import router as search_router
from app.api.v1.chat import router as chat_router
from app.api.v1.cross_meeting import router as cross_meeting_router
from app.api.v1.graph import router as graph_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.live_meetings import router as live_meetings_router


api_router = APIRouter()


@api_router.get("/test", tags=["System"])
async def test_endpoint():
    return {"message": "Knowra API is working"}


api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    live_meetings_router,
    prefix="/meetings",
    tags=["Live Meetings"],
)

api_router.include_router(
    meetings_router,
    prefix="/meetings",
    tags=["Meetings"],
)

api_router.include_router(
    meeting_chat_router,
    prefix="/meetings",
    tags=["Meeting-Scoped Chat"],
)

api_router.include_router(
    media_router,
    tags=["Media"],
)

api_router.include_router(
    transcription_router,
    tags=["Transcription"],
)

api_router.include_router(
    diarization_router,
    tags=["Diarization"],
)

api_router.include_router(
    transcripts_router,
    tags=["Transcript"],
)

api_router.include_router(
    speaker_identity_router,
    tags=["Speaker Identity"],
)

api_router.include_router(
    intelligence_router,
    tags=["Meeting Intelligence"],
)

api_router.include_router(
    actions_router,
    tags=["Action Items"],
)

api_router.include_router(
    decisions_router,
    tags=["Decision Intelligence"],
)

api_router.include_router(
    knowledge_router,
    tags=["Knowledge & Search"],
)

api_router.include_router(
    search_router,
    tags=["Enterprise Search"],
)

api_router.include_router(
    chat_router,
    prefix="/chat",
    tags=["Conversational RAG Chat"],
)

api_router.include_router(
    cross_meeting_router,
    prefix="/cross-meeting",
    tags=["Cross-Meeting Intelligence"],
)

api_router.include_router(
    graph_router,
    prefix="/graph",
    tags=["Organizational Knowledge Graph"],
)

api_router.include_router(
    evaluation_router,
    prefix="/evaluation",
    tags=["AI Evaluation & Observability"],
)

api_router.include_router(
    integrations_router,
    prefix="/integrations",
    tags=["Enterprise Integrations"],
)

api_router.include_router(
    webhooks_router,
    prefix="/webhooks",
    tags=["Enterprise Webhooks"],
)