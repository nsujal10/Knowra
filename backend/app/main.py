from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.database import engine, Base

# Create tables for simple script execution without alembic overhead in tests
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Knowra API", version="0.1.0")

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api/v1")
