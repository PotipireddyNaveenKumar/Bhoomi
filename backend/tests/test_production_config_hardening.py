import os
import pytest
from unittest.mock import patch
from app.core.config import Settings
from app.services.voice.factory import get_voice_provider
from app.services.llm.factory import get_llm_provider


def test_dev_defaults():
    """Verifies default behavior in local development without overrides."""
    with patch.dict(os.environ, {}, clear=True):
        s = Settings(
            ENVIRONMENT="development",
            APP_ENV="development",
            DATABASE_URL="sqlite+aiosqlite:///./bhoomi.db",
            _env_file=None
        )
        assert s.is_production is False
        assert s.DEBUG is True
        assert s.DATABASE_URL == "sqlite+aiosqlite:///./bhoomi.db"
        assert s.DATABASE_SYNC_URL == "sqlite:///./bhoomi.db"
        assert s.SECRET_KEY is not None
        assert "dev" in s.SECRET_KEY


def test_postgresql_url_normalization():
    """Verifies that postgresql://, postgres://, and postgresql+psycopg2:// normalize to postgresql+asyncpg:// without modifying query params or credentials."""
    neon_url = "postgresql://neondb_owner:npg_secret123@ep-cool-fog-a123.asia-south1.aws.neon.tech/neondb?sslmode=require"
    s = Settings(
        ENVIRONMENT="development",
        DATABASE_URL=neon_url,
        _env_file=None
    )
    expected = "postgresql+asyncpg://neondb_owner:npg_secret123@ep-cool-fog-a123.asia-south1.aws.neon.tech/neondb?sslmode=require"
    assert s.DATABASE_URL == expected

    # Test postgres:// format
    postgres_url = "postgres://user:pass@localhost:5432/bhoomi?ssl=require"
    s2 = Settings(ENVIRONMENT="development", DATABASE_URL=postgres_url, _env_file=None)
    assert s2.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/bhoomi?ssl=require"

    # Test postgresql+psycopg2:// format
    psycopg_url = "postgresql+psycopg2://user:pass@localhost:5432/bhoomi"
    s3 = Settings(ENVIRONMENT="development", DATABASE_URL=psycopg_url, _env_file=None)
    assert s3.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/bhoomi"

    # Test already normalized format
    async_url = "postgresql+asyncpg://user:pass@localhost:5432/bhoomi"
    s4 = Settings(ENVIRONMENT="development", DATABASE_URL=async_url, _env_file=None)
    assert s4.DATABASE_URL == async_url


def test_production_rejects_missing_secret_key():
    """Verifies that production fails clearly if SECRET_KEY is missing, default, or insecure."""
    # Missing secret key
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@localhost/db",
            SECRET_KEY=None,
            _env_file=None
        )

    # Insecure default placeholder
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@localhost/db",
            SECRET_KEY="bhoomi_v2_super_secure_jwt_secret_key_change_in_production_2026",
            _env_file=None
        )

    # Too short
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@localhost/db",
            SECRET_KEY="short_key",
            _env_file=None
        )


def test_production_rejects_missing_database_url_or_sqlite():
    """Verifies that production rejects missing database URL or SQLite fallback."""
    # Missing DATABASE_URL
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="very_long_production_secret_key_32_bytes_ok",
            DATABASE_URL=None,
            _env_file=None
        )

    # SQLite attempted in production
    with pytest.raises(ValueError, match="SQLite is not permitted"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="very_long_production_secret_key_32_bytes_ok",
            DATABASE_URL="sqlite+aiosqlite:///./prod.db",
            _env_file=None
        )


def test_production_debug_defaults_to_false():
    """Verifies DEBUG defaults to False in production unless explicitly set."""
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="very_long_production_secret_key_32_bytes_ok",
        DATABASE_URL="postgresql://u:p@localhost/db",
        _env_file=None
    )
    assert s.DEBUG is False
    assert s.is_production is True

    # Explicit override to True allowed
    s_explicit = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="very_long_production_secret_key_32_bytes_ok",
        DATABASE_URL="postgresql://u:p@localhost/db",
        DEBUG=True,
        _env_file=None
    )
    assert s_explicit.DEBUG is True


def test_database_sync_url_optional_in_production():
    """Verifies DATABASE_SYNC_URL is not required for production startup."""
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="very_long_production_secret_key_32_bytes_ok",
        DATABASE_URL="postgresql://u:p@localhost/db",
        DATABASE_SYNC_URL=None,
        _env_file=None
    )
    assert s.DATABASE_SYNC_URL is None


def test_cors_origins_parsing():
    """Verifies BACKEND_CORS_ORIGINS parses comma-separated lists and JSON arrays."""
    s1 = Settings(
        ENVIRONMENT="development",
        BACKEND_CORS_ORIGINS="https://bhoomi.run.app, https://review.dev",
        _env_file=None
    )
    assert s1.BACKEND_CORS_ORIGINS == ["https://bhoomi.run.app", "https://review.dev"]

    s2 = Settings(
        ENVIRONMENT="development",
        BACKEND_CORS_ORIGINS='["https://bhoomi.run.app"]',
        _env_file=None
    )
    assert s2.BACKEND_CORS_ORIGINS == ["https://bhoomi.run.app"]


def test_production_sarvam_requires_credentials_no_silent_mock():
    """Verifies that in production, Sarvam voice provider raises RuntimeError rather than falling back to Mock."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "VOICE_PROVIDER": "sarvam", "SARVAM_API_KEY": ""}):
        with pytest.raises(RuntimeError, match="SARVAM_API_KEY must be provided"):
            get_voice_provider()


def test_production_gemini_requires_credentials_no_silent_mock():
    """Verifies that in production, Gemini provider raises RuntimeError rather than falling back to Mock."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "LLM_PROVIDER": "gemini", "GEMINI_API_KEY": ""}):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY must be provided"):
            get_llm_provider()


def test_non_production_allows_safe_mock_fallback():
    """Verifies that in development/test, missing credentials safely fall back to Mock."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development", "VOICE_PROVIDER": "sarvam", "SARVAM_API_KEY": ""}):
        provider = get_voice_provider()
        assert provider.__class__.__name__ == "MockVoiceProvider"

    with patch.dict(os.environ, {"ENVIRONMENT": "development", "LLM_PROVIDER": "gemini", "GEMINI_API_KEY": ""}):
        llm = get_llm_provider()
        assert llm.__class__.__name__ == "MockLLMProvider"
