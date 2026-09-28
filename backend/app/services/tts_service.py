import io
import re
import logging
from gtts import gTTS
from groq import Groq, BadRequestError, APIError
from app.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    """
    Text-to-Speech synthesis service using official Groq SDK (canopylabs/orpheus-v1-english).
    Sanitizes Markdown formatting before converting text to audio bytes.
    Falls back gracefully to gTTS if Groq API key is missing or model terms acceptance is required.
    """

    def __init__(self):
        self.groq_key = getattr(settings, "GROQ_API_KEY", "")

    def _get_groq_client(self) -> Groq | None:
        if self.groq_key and not self.groq_key.startswith("your_") and len(self.groq_key.strip()) > 10:
            try:
                return Groq(api_key=self.groq_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq SDK client for TTS: {e}")
        return None

    @staticmethod
    def sanitize_text_for_speech(text: str) -> str:
        """
        Strips markdown formatting, code blocks, URLs, and special symbols
        so the synthesized speech sounds natural.
        """
        if not text:
            return ""

        # Remove code blocks ```...```
        cleaned = re.sub(r'```[\s\S]*?```', ' [Code block omitted] ', text)
        
        # Remove inline code `...`
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)

        # Remove markdown headers (# Title)
        cleaned = re.sub(r'^#+\s+', '', cleaned, flags=re.MULTILINE)

        # Remove markdown bold/italic (**text**, *text*, ___text___)
        cleaned = re.sub(r'[*_]{1,3}([^*_]+)[*_]{1,3}', r'\1', cleaned)

        # Remove markdown links [text](url) -> text
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)

        # Remove bullet points / lists (- item, * item, 1. item)
        cleaned = re.sub(r'^\s*[-*+]\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)

        # Remove extra whitespace/newlines
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    def synthesize(
        self,
        text: str,
        voice: str = "troy",
        model: str = "canopylabs/orpheus-v1-english",
        lang: str = "en"
    ) -> tuple[bytes, str]:
        """
        Converts input text into audio bytes.
        Returns a tuple of (audio_bytes, media_type).
        """
        clean_text = self.sanitize_text_for_speech(text)
        if not clean_text:
            clean_text = "No speakable text content available."
        elif len(clean_text) > 3500:
            clean_text = clean_text[:3500] + "..."

        logger.info(f"Synthesizing TTS audio for clean text (length {len(clean_text)} chars)")

        # 1. Attempt Groq SDK Audio Speech API
        client = self._get_groq_client()
        if client:
            try:
                logger.info(f"Requesting Groq Speech API: model={model}, voice={voice}")
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=clean_text,
                    response_format="wav"
                )
                audio_bytes = response.content if hasattr(response, "content") else response.read()
                logger.info(f"Groq TTS synthesis succeeded: {len(audio_bytes)} bytes WAV")
                return audio_bytes, "audio/wav"
            except BadRequestError as e:
                logger.warning(f"Groq TTS BadRequestError: {e}")
                if "model_terms_required" in str(e):
                    logger.info("Groq terms acceptance required for canopylabs/orpheus-v1-english. Using gTTS fallback.")
            except APIError as e:
                logger.warning(f"Groq TTS APIError: {e}. Falling back to gTTS.")
            except Exception as e:
                logger.warning(f"Groq TTS error ({type(e).__name__}): {e}. Falling back to gTTS.")

        # 2. Fallback to gTTS
        try:
            logger.info("Synthesizing audio via gTTS fallback engine")
            tts = gTTS(text=clean_text, lang=lang, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.getvalue(), "audio/mpeg"
        except Exception as e:
            logger.error(f"gTTS synthesis fallback failed: {e}")
            raise RuntimeError(f"Text-to-Speech synthesis failed: {str(e)}")

# Singleton instance
tts_service = TTSService()

