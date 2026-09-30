import os
import logging
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Repository root (…/DisputeIQ). Relative paths (DB file, datasets, evaluation output)
# resolve against this, so the app behaves the same regardless of the working directory.
BASE_DIR = Path(__file__).resolve().parents[3]

load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("disputeiq.config")

_PLACEHOLDER_SECRETS = {"", "change-me", "your_jwt_secret_here"}


def _resolve_sqlite_url(url: str) -> str:
    """Anchors relative SQLite paths (sqlite:///./x.db) to the repository root."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path = url[len(prefix):]
    if path == ":memory:" or os.path.isabs(path):
        return url
    return prefix + str((BASE_DIR / path).resolve()).replace("\\", "/")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    ENV: str = os.getenv("ENV", "development")
    PORT: int = int(os.getenv("PORT", 8000))
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DATABASE_URL: str = _resolve_sqlite_url(os.getenv("DATABASE_URL", "sqlite:///./disputeiq.db"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.75))

    # Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Comma-separated list of allowed browser origins
    CORS_ORIGINS: list = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if o.strip()
    ]

    # Development conveniences (both should be false in production)
    AUTO_MIGRATE: bool = _bool("AUTO_MIGRATE", True)
    SEED_DEMO_DATA: bool = _bool("SEED_DEMO_DATA", True)
    EVIDENCE_MAX_FILE_SIZE: int = int(os.getenv("EVIDENCE_MAX_FILE_SIZE", 10 * 1024 * 1024))
    ENABLE_VLM_PROCESSING: bool = _bool("ENABLE_VLM_PROCESSING", False)

    @property
    def is_development(self) -> bool:
        return self.ENV in {"development", "test"}


settings = Settings()

if settings.JWT_SECRET_KEY in _PLACEHOLDER_SECRETS:
    if not settings.is_development:
        raise RuntimeError("JWT_SECRET_KEY must be set to a strong random value outside development.")
    # Ephemeral key: tokens stop working whenever the process restarts. Set JWT_SECRET_KEY in .env to avoid this.
    settings.JWT_SECRET_KEY = secrets.token_urlsafe(64)
    logger.warning("JWT_SECRET_KEY is not set; using an ephemeral development key.")
