import logging
import httpx
from typing import Dict, Any, Optional
from app.config import Settings

logger = logging.getLogger("voxvision.speech_service")

class SpeechService:
    """
    Modular Speech-to-Text (STT) service supporting Groq Whisper, OpenAI Whisper, and Mock engine.
    """
    def __init__(self):
        self.groq_stt_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        self.openai_stt_url = "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm", mime_type: str = "audio/webm") -> Dict[str, Any]:
        settings = Settings()
        groq_key = settings.GROQ_API_KEY.strip()
        openai_key = settings.OPENAI_API_KEY.strip()

        # 1. Try Groq Whisper API (High-speed LPU)
        if groq_key and len(groq_key) > 10 and not groq_key.startswith("your_"):
            logger.info(f"Transcribing audio using Groq Whisper API (whisper-large-v3-turbo)...")
            try:
                files = {
                    "file": (filename, audio_bytes, mime_type)
                }
                data = {
                    "model": "whisper-large-v3-turbo",
                    "response_format": "json"
                }
                headers = {
                    "Authorization": f"Bearer {groq_key}"
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.groq_stt_url, files=files, data=data, headers=headers)
                    if response.status_code == 200:
                        res_json = response.json()
                        text = res_json.get("text", "").strip()
                        if text:
                            return {
                                "status": "success",
                                "provider": "groq-whisper",
                                "model": "whisper-large-v3-turbo",
                                "text": text
                            }
                        else:
                            return {
                                "status": "warning",
                                "provider": "groq-whisper",
                                "model": "whisper-large-v3-turbo",
                                "message": "No speech detected in recorded audio.",
                                "text": ""
                            }
                    else:
                        error_detail = response.text[:200]
                        logger.error(f"Groq Whisper HTTP {response.status_code}: {error_detail}")
                        return {
                            "status": "error",
                            "provider": "groq-whisper",
                            "model": "whisper-large-v3-turbo",
                            "message": f"Groq Whisper API returned status {response.status_code}.",
                            "text": ""
                        }
            except Exception as e:
                logger.error(f"Groq Whisper transcription exception: {e}")
                return {
                    "status": "error",
                    "provider": "groq-whisper",
                    "message": f"Speech transcription failed: {str(e)}",
                    "text": ""
                }

        # 2. Try OpenAI Whisper API Fallback
        if openai_key and len(openai_key) > 10 and not openai_key.startswith("your_"):
            logger.info("Transcribing audio using OpenAI Whisper API (whisper-1)...")
            try:
                files = {"file": (filename, audio_bytes, mime_type)}
                data = {"model": "whisper-1"}
                headers = {"Authorization": f"Bearer {openai_key}"}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.openai_stt_url, files=files, data=data, headers=headers)
                    if response.status_code == 200:
                        res_json = response.json()
                        return {
                            "status": "success",
                            "provider": "openai-whisper",
                            "model": "whisper-1",
                            "text": res_json.get("text", "").strip()
                        }
            except Exception as e:
                logger.error(f"OpenAI Whisper transcription exception: {e}")

        # 3. Local / Keyless Mock Fallback
        logger.info("Using local mock Speech-to-Text fallback service.")
        return {
            "status": "warning",
            "provider": "mock-speech",
            "model": "mock-whisper-v1",
            "text": "Hello VoxVision AI, explain speech processing in one sentence.",
            "message": "⚠️ GROQ_API_KEY required for live Whisper audio transcription."
        }

speech_service = SpeechService()
