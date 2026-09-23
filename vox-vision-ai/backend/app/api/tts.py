import logging
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Text-to-Speech"])

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize into speech")
    lang: str = Field(default="en", description="ISO language code (default: en)")

@router.post("/tts")
async def generate_speech(request: TTSRequest):
    """
    Synthesizes input text into MP3 audio bytes using gTTS.
    Returns audio/mpeg stream.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")

    try:
        audio_bytes = tts_service.synthesize(text=request.text, lang=request.lang)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
