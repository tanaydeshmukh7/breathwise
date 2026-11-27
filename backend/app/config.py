"""Centralized application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List, Tuple, Type

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BACKEND_ROOT / ".env"
INSECURE_JWT_PLACEHOLDERS = {
    "dev-only-insecure-secret-change-in-production-32bytes",
    "replace-with-a-secure-random-64-char-secret",
}


def _dedupe_models(primary: str, csv_list: str) -> List[str]:
    """Return ordered, deduplicated model identifiers with primary first."""
    seen: set[str] = set()
    ordered: List[str] = []
    for candidate in [primary, *csv_list.split(",")]:
        cleaned = candidate.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


class Settings(BaseSettings):
    """Application settings sourced from backend/.env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Explicit init kwargs (tests) > backend/.env > OS env > secrets
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    APP_NAME: str = "BreatheWise API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Auth & JWT
    JWT_SECRET_KEY: str = Field(
        default="dev-only-insecure-secret-change-in-production-32bytes"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # MongoDB Atlas (PyMongo Async API)
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "breathewise"
    DEV_MEMORY_DB_FALLBACK: bool = True

    # Active AI Provider ("gemini" | "huggingface")
    AI_PROVIDER: str = "gemini"

    # Google Gemini API (official google-genai SDK)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_AVAILABLE_MODELS: str = "gemini-3.5-flash-lite,gemini-3.6-flash,gemini-3.1-flash-lite"
    GEMINI_TIMEOUT_SECONDS: float = 35.0

    # Hugging Face Inference Providers (retained for optional provider switching)
    HF_TOKEN: str = ""
    HF_BASE_URL: str = "https://router.huggingface.co/v1"
    HF_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    HF_FALLBACK_MODELS: str = "Qwen/Qwen3-32B,Qwen/Qwen3-14B,Qwen/Qwen3.5-9B"
    HF_TIMEOUT_SECONDS: float = 35.0

    # Environmental Data Provider
    ENVIRONMENTAL_PROVIDER: str = "open_meteo"
    DEFAULT_CITY: str = "Pune"
    DEFAULT_LATITUDE: float = 18.5204
    DEFAULT_LONGITUDE: float = 73.8567

    # Rate limits
    AI_RATE_LIMIT_PER_MINUTE: int = 20
    AUTH_RATE_LIMIT_PER_MINUTE: int = 30

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def available_gemini_models(self) -> List[str]:
        return _dedupe_models(self.GEMINI_MODEL, self.GEMINI_AVAILABLE_MODELS)

    @property
    def available_qwen_models(self) -> List[str]:
        return _dedupe_models(self.HF_MODEL, self.HF_FALLBACK_MODELS)

    @property
    def has_secure_jwt_secret(self) -> bool:
        secret = self.JWT_SECRET_KEY.strip()
        return len(secret) >= 32 and secret not in INSECURE_JWT_PLACEHOLDERS

    def check_production_security(self) -> List[str]:
        """Return security warnings when production configuration uses unsafe defaults."""
        warnings: List[str] = []
        if self.ENVIRONMENT.lower() == "production":
            if not self.has_secure_jwt_secret:
                warnings.append("JWT_SECRET_KEY uses a placeholder or is shorter than 32 chars.")
            if self.DEBUG:
                warnings.append("DEBUG mode should be disabled in production.")
        return warnings

    @property
    def active_ai_provider(self) -> str:
        provider = self.AI_PROVIDER.strip().lower()
        return provider if provider in ("gemini", "huggingface") else "gemini"

    @property
    def active_ai_model(self) -> str:
        return (
            self.GEMINI_MODEL.strip()
            if self.active_ai_provider == "gemini"
            else self.HF_MODEL.strip()
        )

    @property
    def active_available_models(self) -> List[str]:
        return (
            self.available_gemini_models
            if self.active_ai_provider == "gemini"
            else self.available_qwen_models
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
