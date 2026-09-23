from fastapi import APIRouter
from datetime import datetime, timezone
from app.config import settings

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify backend status and system metadata.
    """
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0"
    }
