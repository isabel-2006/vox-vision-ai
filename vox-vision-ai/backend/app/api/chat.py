from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatMessageResponse(BaseModel):
    reply: str
    status: str
    timestamp: str

@router.post("/placeholder", response_model=ChatMessageResponse)
async def chat_placeholder(payload: ChatMessageRequest):
    """
    Placeholder endpoint for Step 1 frontend integration testing.
    Echos back acknowledgement of user message until AI models are hooked up in Step 2+.
    """
    user_text = payload.message.strip()
    return ChatMessageResponse(
        reply=f"VoxVision AI received: '{user_text}'. (Step 1 Foundation active - AI engine connection coming in Step 2)",
        status="success",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
