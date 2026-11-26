"""BreatheWise FastAPI application entry point."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import db_manager
from app.routes import ai, auth, environment, health, impact, routines, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("breathewise")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    for warning in settings.check_production_security():
        logger.warning("Security config warning: %s", warning)
    await db_manager.connect(settings)
    yield
    await db_manager.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "BreatheWise — AI-Powered Urban Air Quality Assistant API. "
            "Combines verified Open-Meteo environmental & weather telemetry, "
            "documented CPCB Indian NAQI + US EPA AQI indexing, PyMongo Async persistence, "
            "and Google Gemini AI recommendations via the official google-genai SDK."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(self)")
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        logger.exception("Unhandled server error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected internal error occurred."},
        )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(environment.router)
    app.include_router(ai.router)
    app.include_router(users.router)
    app.include_router(routines.router)
    app.include_router(impact.router)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "tagline": "Breathe Smarter. Live Better.",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()
