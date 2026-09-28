import logging
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Text-to-Speech"])

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize into speech")
    voice: str = Field(default="troy", description="Orpheus voice name (e.g., troy)")
    model: str = Field(default="canopylabs/orpheus-v1-english", description="Groq TTS model ID")
    lang: str = Field(default="en", description="ISO language code (default: en)")

@router.post("/tts")
async def generate_speech(request: TTSRequest):
    """
    Synthesizes input text into audio bytes using Groq SDK (canopylabs/orpheus-v1-english) with gTTS fallback.
    Returns audio/wav or audio/mpeg stream.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")

    try:
        audio_bytes, media_type = tts_service.synthesize(
            text=request.text,
            voice=request.voice,
            model=request.model,
            lang=request.lang
        )
        return Response(content=audio_bytes, media_type=media_type)
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

