from fastapi import APIRouter, File, UploadFile, HTTPException
import logging
from app.services.speech_service import speech_service

logger = logging.getLogger("voxvision.speech_api")

router = APIRouter(prefix="/api", tags=["Speech"])

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Speech-to-Text Endpoint.
    Accepts recorded audio file (webm / wav) and transcribes speech using Whisper AI.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No audio file uploaded.")

    try:
        audio_bytes = await file.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file provided.")

        filename = file.filename or "speech.webm"
        mime_type = file.content_type or "audio/webm"

        result = await speech_service.transcribe(audio_bytes, filename=filename, mime_type=mime_type)
        return result

    except Exception as e:
        logger.error(f"STT API exception: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing error: {str(e)}")
