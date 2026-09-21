from pydantic import BaseModel
from typing import List, Optional


class Citation(BaseModel):
    timestamp_seconds: int
    label: str


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    citations: Optional[List[Citation]] = None


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    citations: List[Citation] = []
