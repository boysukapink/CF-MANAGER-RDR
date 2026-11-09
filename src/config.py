"""Centralized Application Configuration.
Loads settings from environment variables and optional .env file.
Adheres to 12-factor configuration principles and zero-secret hardcoding.
"""

import os
from pathlib import Path
from typing import NamedTuple

try:
    from dotenv import load_dotenv

    # Locate project root (one level up from src/)
    _root_dir = Path(__file__).resolve().parent.parent
    _env_file = _root_dir / ".env"
    if _env_file.is_file():
        load_dotenv(dotenv_path=_env_file, override=False)
except ImportError:
    pass


class Settings(NamedTuple):
    """Immutable application settings container."""

    # Application Metadata
    APP_NAME: str = os.getenv("APP_NAME", "FlareRedirect")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_ENV: str = os.getenv("APP_ENV", "production")  # production | development | testing

    # Cloudflare API Base Endpoint
    CLOUDFLARE_API_BASE_URL: str = os.getenv(
        "CLOUDFLARE_API_BASE_URL", "https://api.cloudflare.com/client/v4"
    )

    # HTTP Client Timeouts (seconds)
    TIMEOUT_CONNECT: float = float(os.getenv("CF_TIMEOUT_CONNECT", "10.0"))
    TIMEOUT_READ: float = float(os.getenv("CF_TIMEOUT_READ", "25.0"))
    TIMEOUT_WRITE: float = float(os.getenv("CF_TIMEOUT_WRITE", "15.0"))
    TIMEOUT_POOL: float = float(os.getenv("CF_TIMEOUT_POOL", "10.0"))

    # User-Agent Header
    USER_AGENT: str = os.getenv(
        "CF_USER_AGENT",
        f"{os.getenv('APP_NAME', 'FlareRedirect')}/{os.getenv('APP_VERSION', '1.0.0')}",
    )

    # Cloudflare API Pagination & Rate Limits
    ZONES_PER_PAGE: int = int(os.getenv("CF_ZONES_PER_PAGE", "50"))

    # Memory Audit Log Capacity
    MAX_AUDIT_LOG_ENTRIES: int = int(os.getenv("MAX_AUDIT_LOG_ENTRIES", "2000"))


# Global configuration singleton
settings = Settings()

