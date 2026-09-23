import io
import re
import logging
from gtts import gTTS

logger = logging.getLogger(__name__)

class TTSService:
    """
    Text-to-Speech synthesis service using gTTS (Google Text-to-Speech).
    Sanitizes Markdown formatting before converting text to MP3 audio bytes.
    """

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

    def synthesize(self, text: str, lang: str = "en") -> bytes:
        """
        Converts input text into MP3 audio bytes.
        """
        clean_text = self.sanitize_text_for_speech(text)
        if not clean_text:
            clean_text = "No speakable text content available."

        logger.info(f"Synthesizing TTS audio (length {len(clean_text)} chars)")

        try:
            tts = gTTS(text=clean_text, lang=lang, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.getvalue()
        except Exception as e:
            logger.error(f"gTTS synthesis error: {e}")
            raise RuntimeError(f"Text-to-Speech synthesis failed: {str(e)}")

# Singleton instance
tts_service = TTSService()
