"""Unit tests for centralized configuration management.
"""

import os
from pathlib import Path
from src.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.APP_NAME == "FlareRedirect"
    assert s.APP_VERSION == "1.0.0"
    assert s.APP_ENV in ("production", "development", "testing")
    assert s.CLOUDFLARE_API_BASE_URL == "https://api.cloudflare.com/client/v4"
    assert s.TIMEOUT_CONNECT == 10.0
    assert s.TIMEOUT_READ == 25.0
    assert s.ZONES_PER_PAGE == 50
    assert s.MAX_AUDIT_LOG_ENTRIES == 2000


def test_env_example_file_exists():
    root = Path(__file__).resolve().parent.parent
    env_example = root / ".env.example"
    assert env_example.is_file()
    content = env_example.read_text(encoding="utf-8")
    assert "CLOUDFLARE_API_BASE_URL" in content
    assert "CF_TIMEOUT_CONNECT" in content
    assert "MAX_AUDIT_LOG_ENTRIES" in content

