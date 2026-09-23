import logging
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.config import settings, Settings

logger = logging.getLogger("voxvision.llm_service")

class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM providers in VoxVision AI.
    All LLM providers must implement `generate_response`.
    """
    @abstractmethod
    async def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM Integration using Google REST API.
    """
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    async def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("your_") or len(self.api_key.strip()) < 10:
            logger.warning("Gemini API key is not configured in backend/.env")
            return {
                "status": "warning",
                "provider": "gemini",
                "model": self.model_name,
                "reply": "⚠️ **Gemini API Key Required**: Please configure `GEMINI_API_KEY` in your `backend/.env` file to enable live Gemini AI responses.\n\n*(Falling back to VoxVision AI local mode)*",
                "error_code": "MISSING_API_KEY"
            }

        # Build contents from history and current prompt
        contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                text = item.get("content", "")
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }

        url = f"{self.base_url}?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            ai_text = parts[0]["text"]
                            return {
                                "status": "success",
                                "provider": "gemini",
                                "model": self.model_name,
                                "reply": ai_text
                            }
                    
                    return {
                        "status": "error",
                        "provider": "gemini",
                        "model": self.model_name,
                        "reply": "Unexpected empty response payload from Gemini API.",
                        "error_code": "EMPTY_RESPONSE"
                    }
                else:
                    error_msg = f"Gemini API HTTP {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return {
                        "status": "error",
                        "provider": "gemini",
                        "model": self.model_name,
                        "reply": f"❌ **LLM Service Error**: Gemini API returned HTTP status {response.status_code}. Please check your API key and quotas.",
                        "error_code": f"HTTP_{response.status_code}"
                    }
        except httpx.TimeoutException:
            logger.error("Gemini API request timed out after 30 seconds.")
            return {
                "status": "error",
                "provider": "gemini",
                "model": self.model_name,
                "reply": "⏱️ **Timeout Error**: Request to Gemini API timed out after 30s. Please try again.",
                "error_code": "TIMEOUT"
            }
        except Exception as e:
            logger.error(f"Gemini API request error: {e}")
            return {
                "status": "error",
                "provider": "gemini",
                "model": self.model_name,
                "reply": f"⚠️ **Connection Failure**: Unable to connect to Gemini API ({str(e)}).",
                "error_code": "CONNECTION_ERROR"
            }


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM Integration using OpenAI REST API.
    """
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name
        self.url = "https://api.openai.com/v1/chat/completions"

    async def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("your_") or len(self.api_key.strip()) < 10:
            logger.warning("OpenAI API key is not configured in backend/.env")
            return {
                "status": "warning",
                "provider": "openai",
                "model": self.model_name,
                "reply": "⚠️ **OpenAI API Key Required**: Please configure `OPENAI_API_KEY` in your `backend/.env` file.",
                "error_code": "MISSING_API_KEY"
            }

        messages = [{"role": "system", "content": "You are VoxVision AI, a helpful, precise multimodal assistant."}]
        if history:
            for item in history:
                messages.append({"role": item.get("role", "user"), "content": item.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        ai_text = choices[0]["message"]["content"]
                        return {
                            "status": "success",
                            "provider": "openai",
                            "model": self.model_name,
                            "reply": ai_text
                        }
                    return {
                        "status": "error",
                        "provider": "openai",
                        "model": self.model_name,
                        "reply": "Empty response from OpenAI API.",
                        "error_code": "EMPTY_RESPONSE"
                    }
                else:
                    return {
                        "status": "error",
                        "provider": "openai",
                        "model": self.model_name,
                        "reply": f"❌ **OpenAI API Error**: Status {response.status_code}.",
                        "error_code": f"HTTP_{response.status_code}"
                    }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "status": "error",
                "provider": "openai",
                "model": self.model_name,
                "reply": f"⚠️ **Connection Failure**: OpenAI API request failed ({str(e)}).",
                "error_code": "CONNECTION_ERROR"
            }


class MockLLMProvider(BaseLLMProvider):
    """
    Local Mock Provider for testing VoxVision AI offline or without API keys.
    """
    def __init__(self, model_name: str = "voxvision-mock-v1"):
        self.model_name = model_name

    async def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        lower_prompt = prompt.lower()
        
        if "step 1" in lower_prompt or "step 2" in lower_prompt or "step 3" in lower_prompt:
            reply = "VoxVision AI is built in modular steps:\n- **Step 1**: FastAPI foundation & Vanilla JS dark UI.\n- **Step 2**: Real-time WebSocket connection manager & ping/pong.\n- **Step 3**: Modular LLM service layer for backend AI inference!"
        elif "architecture" in lower_prompt or "how do you work" in lower_prompt:
            reply = "VoxVision AI uses a decoupled architecture:\n`Frontend (Vanilla JS)` $\\rightarrow$ `WebSocket (/ws/chat)` $\\rightarrow$ `FastAPI Backend` $\\rightarrow$ `Modular LLM Service (Gemini/OpenAI)`."
        else:
            reply = f"VoxVision AI (Mock Engine): I received your prompt: '{prompt}'. To switch to live LLM generation, set `GEMINI_API_KEY` in `backend/.env`!"

        return {
            "status": "success",
            "provider": "mock",
            "model": self.model_name,
            "reply": reply
        }


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM Integration using Groq OpenAI-compatible REST API.
    Base URL: https://api.groq.com/openai/v1/chat/completions
    """
    def __init__(self, api_key: str, model_name: str = "openai/gpt-oss-120b"):
        self.api_key = api_key
        self.model_name = model_name
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("your_") or len(self.api_key.strip()) < 10:
            logger.warning("Groq API key is not configured in backend/.env")
            return {
                "status": "warning",
                "provider": "groq",
                "model": self.model_name,
                "reply": "⚠️ **Groq API Key Required**: Please configure `GROQ_API_KEY` in your `backend/.env` file to enable live Groq LPU responses.\n\n*(Falling back to VoxVision AI local mode)*",
                "error_code": "MISSING_API_KEY"
            }

        messages = [{"role": "system", "content": "You are VoxVision AI, an intelligent, fast multimodal assistant powered by Groq."}]
        if history:
            for item in history:
                messages.append({"role": item.get("role", "user"), "content": item.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        ai_text = choices[0]["message"].get("content", "")
                        return {
                            "status": "success",
                            "provider": "groq",
                            "model": self.model_name,
                            "reply": ai_text
                        }
                    return {
                        "status": "error",
                        "provider": "groq",
                        "model": self.model_name,
                        "reply": "Empty message payload received from Groq API.",
                        "error_code": "EMPTY_RESPONSE"
                    }
                elif response.status_code == 401:
                    logger.error("Groq API key is invalid or unauthorized.")
                    return {
                        "status": "error",
                        "provider": "groq",
                        "model": self.model_name,
                        "reply": "❌ **Groq Authentication Error**: Invalid or unauthorized `GROQ_API_KEY`. Please check your API key in `backend/.env`.",
                        "error_code": "UNAUTHORIZED"
                    }
                elif response.status_code == 429:
                    logger.error("Groq API rate limit or quota exceeded.")
                    return {
                        "status": "error",
                        "provider": "groq",
                        "model": self.model_name,
                        "reply": "⏳ **Rate Limit Exceeded**: Groq API rate limit reached. Please wait a moment and try again.",
                        "error_code": "RATE_LIMIT"
                    }
                else:
                    error_detail = response.text[:200]
                    logger.error(f"Groq API HTTP {response.status_code}: {error_detail}")
                    return {
                        "status": "error",
                        "provider": "groq",
                        "model": self.model_name,
                        "reply": f"❌ **Groq API Error**: Status {response.status_code} ({self.model_name}). Please verify model availability and parameters.",
                        "error_code": f"HTTP_{response.status_code}"
                    }
        except httpx.TimeoutException:
            logger.error("Groq API request timed out after 30 seconds.")
            return {
                "status": "error",
                "provider": "groq",
                "model": self.model_name,
                "reply": "⏱️ **Timeout Error**: Request to Groq API timed out after 30s.",
                "error_code": "TIMEOUT"
            }
        except Exception as e:
            logger.error(f"Groq API connection exception: {e}")
            return {
                "status": "error",
                "provider": "groq",
                "model": self.model_name,
                "reply": f"⚠️ **Connection Failure**: Unable to connect to Groq API ({str(e)}).",
                "error_code": "CONNECTION_ERROR"
            }


class LLMServiceManager:
    """
    Service Factory that initializes and manages the active LLM provider.
    """
    def __init__(self):
        self.provider = self._create_provider()

    def _create_provider(self) -> BaseLLMProvider:
        current_settings = Settings()
        provider_type = current_settings.LLM_PROVIDER.lower().strip()
        model_name = current_settings.LLM_MODEL_NAME

        if provider_type == "groq":
            logger.info(f"Initializing Groq Provider with model: {model_name}")
            return GroqProvider(api_key=current_settings.GROQ_API_KEY, model_name=model_name)
        elif provider_type == "gemini":
            logger.info(f"Initializing Gemini Provider with model: {model_name}")
            return GeminiProvider(api_key=current_settings.GEMINI_API_KEY, model_name=model_name)
        elif provider_type == "openai":
            logger.info(f"Initializing OpenAI Provider with model: {model_name}")
            return OpenAIProvider(api_key=current_settings.OPENAI_API_KEY, model_name=model_name)
        else:
            logger.info("Initializing Mock Provider for VoxVision AI")
            return MockLLMProvider(model_name=model_name)

    async def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        # Re-check provider in case settings were updated dynamically
        provider = self._create_provider()
        return await provider.generate_response(prompt, history)

# Global LLM service singleton instance
llm_service = LLMServiceManager()

