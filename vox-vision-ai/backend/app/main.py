from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from app.config import settings, FRONTEND_DIR
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.speech import router as speech_router
from app.api.tts import router as tts_router
from app.api.websocket import router as websocket_router

app = FastAPI(
    title=settings.APP_NAME,
    version="0.5.0",
    description="Backend API foundation for VoxVision AI Multimodal Assistant"
)

# Configure CORS
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(speech_router)
app.include_router(tts_router)
app.include_router(websocket_router)


# Mount Frontend static files at root (after API routers so API routes take precedence)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
