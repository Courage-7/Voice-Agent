"""Neon Serverless PostgreSQL connection pool and query gateway."""

from contextlib import asynccontextmanager
import json
import logging
from typing import Any, List, Optional
import urllib.parse

from app.core.config import settings

logger = logging.getLogger(__name__)


ERR_DB_NOT_CONNECTED = "Database not connected"


class DatabaseGateway:
    """High-performance async connection pool gateway for Neon PostgreSQL."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url
        self._pool: Any = None
        self._is_available: bool = False

    @property
    def is_connected(self) -> bool:
        """Inspect active database availability."""
        return self._pool is not None and self._is_available

    async def connect(self) -> bool:
        """Initialize connection pool to Neon PostgreSQL with fallback support."""
        if settings.demo_mode:
            logger.info("Demo mode active: database pool connection skipped.")
            return False

        dsn = self.database_url or settings.database_url
        if not dsn or not dsn.strip():
            logger.info("DATABASE_URL not configured. Operating in memory-backed mode.")
            self._pool = None
            self._is_available = False
            return False

        # Guard against sample / placeholder URLs
        if any(h in dsn for h in ("example.invalid", "placeholder", "your-project", "example.com")):
            logger.info("Placeholder DATABASE_URL detected. Operating in memory-backed mode.")
            self._pool = None
            self._is_available = False
            return False

        try:
            import asyncpg
        except ImportError:
            logger.warning("asyncpg is not installed. Operating in memory-backed mode.")
            self._pool = None
            self._is_available = False
            return False

        try:
            parsed = urllib.parse.urlparse(dsn)
            # Neon requires SSL; asyncpg handles ssl="require" cleanly
            use_ssl = "neon.tech" in parsed.netloc or "sslmode=require" in dsn

            # Strip query params like sslmode from DSN if passing ssl directly to asyncpg
            clean_dsn = dsn
            if "sslmode=" in clean_dsn:
                clean_dsn = clean_dsn.split("?")[0]

            async def init_connection(conn: asyncpg.Connection) -> None:
                # Transparently encode/decode JSONB to Python dicts
                await conn.set_type_codec(
                    "jsonb",
                    encoder=json.dumps,
                    decoder=json.loads,
                    schema="pg_catalog",
                )
                await conn.set_type_codec(
                    "json",
                    encoder=json.dumps,
                    decoder=json.loads,
                    schema="pg_catalog",
                )

            # When connecting via Neon's connection pooler (-pooler / PgBouncer),
            # prepared statements must be disabled by setting statement_cache_size=0
            statement_cache_size = 0 if ("-pooler" in dsn or "neon.tech" in dsn) else 100

            self._pool = await asyncpg.create_pool(
                dsn=clean_dsn,
                min_size=1,
                max_size=10,
                timeout=10.0,
                command_timeout=15.0,
                ssl="require" if use_ssl else None,
                statement_cache_size=statement_cache_size,
                init=init_connection,
            )

            # Test pool connectivity
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            self._is_available = True
            logger.info("Neon PostgreSQL connection pool initialized successfully.")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to connect to PostgreSQL ({e}). Operating in memory-backed fallback mode."
            )
            self._pool = None
            self._is_available = False
            return False

    async def disconnect(self) -> None:
        """Gracefully terminate connection pool on application shutdown."""
        if self._pool is not None:
            try:
                await self._pool.close()
                logger.info("Neon PostgreSQL connection pool terminated.")
            except Exception as e:
                logger.warning(f"Error closing PostgreSQL pool: {e}")
            finally:
                self._pool = None
                self._is_available = False

    def mark_unavailable(self, reason: str = "") -> None:
        """Mark pool degraded and fail over to in-memory store."""
        if self._is_available:
            self._is_available = False
            logger.warning(f"PostgreSQL connection marked unavailable ({reason}). Switched to fallback.")

    async def fetch(self, query: str, *args: Any) -> List[Any]:
        """Execute query returning all matching records."""
        if not self.is_connected or self._pool is None:
            raise RuntimeError(ERR_DB_NOT_CONNECTED)
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> Optional[Any]:
        """Execute query returning a single record or None."""
        if not self.is_connected or self._pool is None:
            raise RuntimeError(ERR_DB_NOT_CONNECTED)
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Optional[Any]:
        """Execute query returning a scalar value or None."""
        if not self.is_connected or self._pool is None:
            raise RuntimeError(ERR_DB_NOT_CONNECTED)
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        """Execute SQL statement and return status tag."""
        if not self.is_connected or self._pool is None:
            raise RuntimeError(ERR_DB_NOT_CONNECTED)
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch_as_user(self, user_id: str, query: str, *args: Any) -> List[Any]:
        """Run a read query under a transaction-scoped application identity."""
        async with self.user_context(user_id) as conn:
            return await conn.fetch(query, *args)

    async def fetchrow_as_user(self, user_id: str, query: str, *args: Any) -> Optional[Any]:
        """Run a single-row query under a transaction-scoped application identity."""
        async with self.user_context(user_id) as conn:
            return await conn.fetchrow(query, *args)

    async def execute_as_user(self, user_id: str, query: str, *args: Any) -> str:
        """Run a mutation under a transaction-scoped application identity."""
        async with self.user_context(user_id) as conn:
            return await conn.execute(query, *args)

    @asynccontextmanager
    async def user_context(self, user_id: str):
        """Execute scoped database operations with active tenant RLS context."""
        if not self.is_connected or self._pool is None:
            raise RuntimeError(ERR_DB_NOT_CONNECTED)
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET ROLE app_user")
                await conn.execute("SELECT set_config('app.current_user_id', $1, true)", user_id)
                try:
                    yield conn
                finally:
                    await conn.execute("RESET ROLE")

db_gateway = DatabaseGateway()
