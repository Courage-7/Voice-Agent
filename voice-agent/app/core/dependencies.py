"""FastAPI Dependency injection helpers."""

from typing import Generator
from app.core.config import Settings, settings


def get_settings() -> Settings:
    """Dependency provider for application settings."""
    return settings
