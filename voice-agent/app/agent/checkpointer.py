"""Application-owned lifecycle for the durable LangGraph checkpointer."""

import logging
import os
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LangGraphCheckpointer:
    """Own the Postgres checkpointer for the lifetime of this FastAPI process."""

    def __init__(self) -> None:
        self._pool: Any = None
        self.saver: Optional[Any] = None

    async def start(self) -> Optional[Any]:
        """Open the saver and apply its idempotent vendor-managed table setup."""
        if self.saver is not None:
            return self.saver
        if not settings.database_url:
            if settings.requires_persistent_storage:
                raise RuntimeError("DATABASE_URL is required for durable LangGraph state.")
            logger.info("LangGraph checkpointer disabled: DATABASE_URL is not configured.")
            return None

        # Required by the official checkpointer implementation to restrict
        # msgpack decoding to known-safe types.
        os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg.rows import dict_row
            from psycopg_pool import AsyncConnectionPool

            pool = AsyncConnectionPool(
                conninfo=settings.database_url,
                min_size=1,
                max_size=5,
                open=False,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
            )
            await pool.open()
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            self._pool = pool
            self.saver = saver
            logger.info("LangGraph PostgreSQL checkpointer is ready.")
            return saver
        except Exception:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
            if settings.requires_persistent_storage:
                raise
            logger.exception("LangGraph checkpointer unavailable; disabled in non-production environment.")
            return None

    async def stop(self) -> None:
        """Release checkpointer connections during application shutdown."""
        self.saver = None
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


langgraph_checkpointer = LangGraphCheckpointer()
