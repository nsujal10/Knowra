from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.media import router as media_router
from app.api.v1.transcription import router as transcription_router
from app.api.v1.diarization import router as diarization_router
from app.api.v1.transcripts import router as transcripts_router
from app.api.v1.speaker_identity import router as speaker_identity_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.actions import router as actions_router


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
    meetings_router,
    prefix="/meetings",
    tags=["Meetings"],
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