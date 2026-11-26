"""Health & system configuration status routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.database import db_manager

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    """Report real-time status of API, database, environmental provider, and AI config."""
    if db_manager.handle is None:
        await db_manager.connect(settings)
    handle = db_manager.handle
    active_provider = settings.active_ai_provider
    is_gemini = active_provider == "gemini"
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "database": {
            "mode": handle.mode if handle else "unavailable",
            "connected": handle.is_connected if handle else False,
            "detail": handle.detail if handle else "Not initialized",
        },
        "ai": {
            "provider": "google_gemini" if is_gemini else "huggingface_inference_providers",
            "configured": bool(
                settings.GEMINI_API_KEY.strip()
                if is_gemini
                else settings.HF_TOKEN.strip()
            ),
            "active_model": settings.active_ai_model,
            "available_models": settings.active_available_models,
        },
        "environmental_provider": {
            "name": settings.ENVIRONMENTAL_PROVIDER,
            "default_city": settings.DEFAULT_CITY,
        },
    }
