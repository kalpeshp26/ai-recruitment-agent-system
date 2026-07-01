"""
--- FILE: backend/config.py ---

Configuration settings for IntelliHire Interview service.

This module exposes a single `settings` instance of `Settings` which
loads configuration from environment variables (and a .env file when
present) using pydantic-settings BaseSettings.

All variables mirror the documented names in docs/INTERVIEW_CONFIG.md
and are grouped into logical categories.
"""
from typing import Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Fields directly reflect the variables listed in
    docs/INTERVIEW_CONFIG.md. Use `settings = Settings()` to access
    values across the codebase.
    """

    # Model config: read from .env by default
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Session Config
    INTELLIHIRE_MAX_QUESTIONS: int = Field(10, ge=1, le=100)
    INTELLIHIRE_MAX_DURATION_SECONDS: int = Field(1800, ge=60, le=10800)

    # RL Engine Config
    RL_ALPHA: float = Field(0.1, ge=0.0, le=1.0)
    RL_GAMMA: float = Field(0.9, ge=0.0, le=1.0)
    RL_EPSILON_START: float = Field(0.30, ge=0.0, le=1.0)
    RL_EPSILON_MIN: float = Field(0.05, ge=0.0, le=1.0)
    RL_EPSILON_DECAY: float = Field(0.995, gt=0.0, lt=1.0)
    RL_OPTIMISTIC_INIT: float = Field(0.1)

    # AI Model Config
    GROQ_MODEL: str = Field("llama-3.1-70b-versatile")
    GROQ_TEMP_EVAL: float = Field(0.2, ge=0.0, le=1.0)
    GROQ_TEMP_GEN: float = Field(0.7, ge=0.0, le=1.0)
    GROQ_MAX_TOKENS_EVAL: int = Field(512, gt=0)
    GROQ_RATE_LIMIT_RETRIES: int = Field(5, ge=0)

    # Proctoring Config
    PROCTORING_MAX_WARNINGS: int = Field(3, ge=1)
    PROCTORING_WEBCAM_MISSING_THRESHOLD_SECONDS: int = Field(10, ge=1)
    PROCTORING_FACE_CHECK_INTERVAL_SECONDS: int = Field(5, ge=1)

    # Scoring Config
    SCORE_WEIGHT_TECHNICAL: float = Field(0.4, ge=0.0, le=1.0)
    SCORE_WEIGHT_COMMUNICATION: float = Field(0.2, ge=0.0, le=1.0)
    SCORE_WEIGHT_CONFIDENCE: float = Field(0.2, ge=0.0, le=1.0)
    SCORE_WEIGHT_PROBLEM_SOLVING: float = Field(0.2, ge=0.0, le=1.0)
    PENALTY_PER_WARNING: int = Field(2, ge=0)

    # Database Config
    DATABASE_URL: str = Field("sqlite+aiosqlite:///./dev.db")
    SQLALCHEMY_ECHO: bool = Field(False)
    RL_QTABLE_PERSIST_EPSILON: bool = Field(False)

    # API Keys
    GROQ_API_KEY: str = Field("", description="API key for Groq provider")
    SARVAM_TTS_KEY: str = Field("", description="API key for Sarvam TTS")
    S3_BUCKET_URL: str = Field("", description="S3-compatible bucket base URL for audio storage")

    # Frontend Config
    FRONTEND_PORT: int = Field(5173, gt=1024)
    API_BASE_PATH: str = Field("/api/v1/interview")
    STRICT_MODE_REACT_GUARD: bool = Field(True)
    # JWT
    JWT_SECRET: str = Field("changeme", description="HS256 secret for JWT validation")

    @validator(
        "SCORE_WEIGHT_TECHNICAL",
        "SCORE_WEIGHT_COMMUNICATION",
        "SCORE_WEIGHT_CONFIDENCE",
        "SCORE_WEIGHT_PROBLEM_SOLVING",
        pre=True,
    )
    def _ensure_weights_float(cls, v: Any) -> float:
        """Ensure weight fields are parsed as floats."""
        return float(v)

    @validator("SCORE_WEIGHT_PROBLEM_SOLVING")
    def _validate_weights_sum(cls, v: float, values: dict) -> float:
        """Validate that score weights sum to 1.0 (within tolerance).

        This enforces the invariant from INTERVIEW_CONFIG.md that the
        scoring weights must sum to 1.0. A small tolerance (1e-6) is
        permitted for floating point representation.
        """
        tech = values.get("SCORE_WEIGHT_TECHNICAL")
        comm = values.get("SCORE_WEIGHT_COMMUNICATION")
        conf = values.get("SCORE_WEIGHT_CONFIDENCE")
        ps = float(v)
        total = (tech or 0.0) + (comm or 0.0) + (conf or 0.0) + ps
        if abs(total - 1.0) > 1e-6:
            raise ValueError("Score weights must sum to 1.0 across dimensions")
        return v

    def is_sqlite(self) -> bool:
        """Return True if the configured DATABASE_URL points to SQLite.

        Useful for runtime branching between SQLite (dev) and
        PostgreSQL (prod) behavior.
        """
        return self.DATABASE_URL.startswith("sqlite") or "aiosqlite" in self.DATABASE_URL


# Single settings instance exported for application-wide use
settings = Settings()

__all__ = ["settings", "Settings"]
