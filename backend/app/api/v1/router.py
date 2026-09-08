from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/test", tags=["System"])
async def test_endpoint():
    return {"message": "Knowra API is working"}