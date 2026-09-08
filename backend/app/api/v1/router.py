from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.security_test import router as security_router

api_router = APIRouter()

@api_router.get("/test", tags=["System"])
async def test_endpoint():
    return {"message": "Knowra API is working"}

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(security_router, prefix="/security", tags=["Security"])
