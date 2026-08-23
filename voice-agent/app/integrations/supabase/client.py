"""Supabase client initialization with graceful fallback."""

import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseGateway:
    """Gateway for Supabase database operations."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or settings.supabase_url
        self.key = key or settings.supabase_key
        self._client: Any = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.url or not self.key:
            logger.warning("Supabase URL or Key not set. Using in-memory fallback store.")
            return

        try:
            from supabase import create_client
            self._client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully.")
        except Exception:
            logger.exception("Failed to initialize Supabase client")
            self._client = None

    @property
    def client(self) -> Any:
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._client is not None


supabase_gateway = SupabaseGateway()
