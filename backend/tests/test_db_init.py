"""Test database initialization."""

import pytest
import asyncio
from app.db_init import init_db
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_db_init():
    """Test that database initialization works."""
    settings = get_settings()
    
    # This should not raise an error
    try:
        await init_db()
        assert True
    except Exception as e:
        pytest.fail(f"Database initialization failed: {e}")


def test_settings_load():
    """Test that settings can be loaded."""
    settings = get_settings()
    
    assert settings.app_name == "Seedlings API"
    assert settings.database_schema == "seedlings"
    assert settings.llm_provider in ["ollama", "openai"]
