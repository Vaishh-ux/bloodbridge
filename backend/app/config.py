"""Application settings, loaded from environment variables / a local .env file.

Every value here can be overridden with an environment variable of the same name.
See backend/.env.example for documentation of each setting.
"""
import logging
import secrets
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("bloodbridge.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Blood Bridge API"
    VERSION: str = "1.1.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"  # development | production | test

    # --- Database -----------------------------------------------------------------
    # PostgreSQL is the intended database, e.g.
    #   postgresql+psycopg2://bloodbridge:password@localhost:5432/bloodbridge
    # A local SQLite file is used only when DATABASE_URL is not set (quick local dev).
    DATABASE_URL: str = "sqlite:///./bloodbridge_dev.db"

    # --- Security -----------------------------------------------------------------
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # Comma-separated list of allowed browser origins (your frontend URLs).
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Simple per-IP limit for login/registration attempts (requests per minute).
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20

    # --- Matching engine (weights must add up to 1.0) -----------------------------
    WEIGHT_DISTANCE: float = 0.30
    WEIGHT_AVAILABILITY: float = 0.20
    WEIGHT_ELIGIBILITY: float = 0.20
    WEIGHT_EMERGENCY_PRIORITY: float = 0.15
    WEIGHT_RESPONSE_HISTORY: float = 0.10
    WEIGHT_RELIABILITY: float = 0.05
    MAX_MATCH_DISTANCE_KM: float = 50.0
    NOTIFY_TOP_N_DONORS: int = 10

    # --- System screening criteria (configurable; NOT a medical determination) -----
    MIN_DONATION_INTERVAL_DAYS: int = 90
    MIN_DONOR_AGE: int = 18
    MAX_DONOR_AGE: int = 65

    # Decimal places kept when publishing request locations (2 ≈ 1.1 km).
    PUBLIC_LOCATION_DECIMALS: int = 2

    # Optional: path to a built frontend (frontend/dist) to serve from the API.
    FRONTEND_DIST: str = ""

    # Optional: create (or reset the password of) an administrator at startup.
    # Handy on hosts without a command line, e.g. Render's free plan.
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Administrator"

    @field_validator("DATABASE_URL")
    @classmethod
    def normalise_db_url(cls, v: str) -> str:
        # Render/Heroku/Neon often hand out "postgres://" URLs; SQLAlchemy needs "postgresql://".
        if v.startswith("postgres://"):
            v = "postgresql+psycopg2://" + v[len("postgres://"):]
        elif v.startswith("postgresql://"):
            v = "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()

if not settings.JWT_SECRET:
    if settings.is_production:
        raise RuntimeError("JWT_SECRET must be set when ENVIRONMENT=production.")
    settings.JWT_SECRET = secrets.token_urlsafe(48)
    logger.warning(
        "JWT_SECRET is not set; generated a temporary secret. Logins will reset when the "
        "server restarts. Set JWT_SECRET in backend/.env."
    )

if settings.is_production and settings.DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("DATABASE_URL must point to PostgreSQL when ENVIRONMENT=production.")

_weights = (
    settings.WEIGHT_DISTANCE + settings.WEIGHT_AVAILABILITY + settings.WEIGHT_ELIGIBILITY
    + settings.WEIGHT_EMERGENCY_PRIORITY + settings.WEIGHT_RESPONSE_HISTORY + settings.WEIGHT_RELIABILITY
)
if abs(_weights - 1.0) > 0.001:
    logger.warning("Matching weights add up to %.3f instead of 1.0; scores will be rescaled.", _weights)
