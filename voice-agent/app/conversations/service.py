"""Conversation recording and logging service."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.conversations.models import ConversationMessage, ConversationSession
from app.core.config import settings
from app.db.session import db_gateway

logger = logging.getLogger(__name__)


class ConversationService:
    """Service to track live session turns and archive history to Neon PostgreSQL."""

    def __init__(self, max_sessions: int = 500) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._max_sessions = max_sessions

    def _prune_sessions_if_needed(self) -> None:
        """Evict oldest sessions when cache exceeds bounded limit."""
        if len(self._sessions) <= self._max_sessions:
            return
        sorted_keys = sorted(
            self._sessions.keys(),
            key=lambda k: self._sessions[k].created_at,
        )
        excess = len(self._sessions) - self._max_sessions
        for k in sorted_keys[:excess]:
            self._sessions.pop(k, None)

    def get_or_create_session(self, session_id: str, user_id: str = "default_user") -> ConversationSession:
        """Get or initialize a development-only in-process session cache."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id, user_id=user_id)
            self._prune_sessions_if_needed()
        return self._sessions[session_id]

    def _raise_if_persistence_unavailable(self) -> None:
        if settings.requires_persistent_storage and not db_gateway.is_connected:
            raise RuntimeError("Persistent storage is unavailable; refusing to use in-memory session state.")

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        *,
        persona: Optional[str] = None,
        voice_model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession:
        """Create an owned durable session before any transcript or WebSocket activity."""
        if db_gateway.is_connected:
            await db_gateway.execute_as_user(
                user_id,
                """
                INSERT INTO conversation_sessions (session_id, user_id, persona, voice_model, metadata)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (session_id) DO NOTHING
                """,
                session_id,
                user_id,
                persona,
                voice_model,
                metadata or {},
            )
            row = await db_gateway.fetchrow_as_user(
                user_id,
                "SELECT session_id, user_id, created_at, metadata FROM conversation_sessions WHERE session_id = $1",
                session_id,
            )
            if not row:
                raise PermissionError("Conversation session does not belong to the authenticated user.")
            session = self._sessions.get(session_id)
            if session and session.user_id != user_id:
                raise PermissionError("Conversation session does not belong to the authenticated user.")
            if not session:
                data = dict(row)
                session = ConversationSession(
                    session_id=data["session_id"],
                    user_id=data["user_id"],
                    created_at=data["created_at"],
                    metadata=data.get("metadata") or {},
                )
                self._sessions[session_id] = session
                self._prune_sessions_if_needed()
            return session

        self._raise_if_persistence_unavailable()
        return self.get_or_create_session(session_id, user_id)

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a session by session ID from memory cache."""
        return self._sessions.get(session_id)

    async def get_session_async(self, session_id: str, user_id: Optional[str] = None) -> Optional[ConversationSession]:
        """Retrieve a session through the durable ownership record when available."""
        if db_gateway.is_connected:
            try:
                if not user_id:
                    return None
                session_row = await db_gateway.fetchrow_as_user(
                    user_id,
                    "SELECT session_id, user_id, created_at, metadata FROM conversation_sessions WHERE session_id = $1",
                    session_id,
                )
                if not session_row:
                    return None
                cached = self._sessions.get(session_id)
                if cached and cached.user_id == user_id:
                    return cached
                rows = await db_gateway.fetch_as_user(
                    user_id,
                    "SELECT id, session_id, user_id, role, content, metadata, created_at FROM messages WHERE session_id = $1 ORDER BY created_at ASC",
                    session_id,
                )
                data = dict(session_row)
                session = ConversationSession(
                    session_id=data["session_id"],
                    user_id=data["user_id"],
                    created_at=data["created_at"],
                    metadata=data.get("metadata") or {},
                )
                for r in rows:
                    row_dict = dict(r)
                    message_id = row_dict.get("id")
                    created_at = row_dict.get("created_at")
                    if not isinstance(message_id, str) or not isinstance(created_at, datetime):
                        raise RuntimeError("Conversation message row has invalid persisted fields.")
                    session.messages.append(
                        ConversationMessage(
                            id=message_id,
                            role=row_dict.get("role", "user"),
                            content=row_dict.get("content", ""),
                            metadata=row_dict.get("metadata") or {},
                            timestamp=created_at,
                        )
                    )
                self._sessions[session_id] = session
                self._prune_sessions_if_needed()
                return session
            except Exception as e:
                logger.warning(f"Failed to fetch session {session_id} from Neon PostgreSQL: {e}")
                if settings.requires_persistent_storage:
                    raise RuntimeError("Persistent session lookup failed.") from e

        self._raise_if_persistence_unavailable()
        return self.get_session(session_id)

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ConversationSession]:
        """List conversation sessions with pagination, optionally filtered by user."""
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions[offset:offset + limit]

    async def list_sessions_async(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ConversationSession]:
        """List conversation sessions with pagination, hydrating history from Neon PostgreSQL."""
        if db_gateway.is_connected and user_id:
            try:
                query = """
                SELECT session_id, user_id, created_at
                FROM conversation_sessions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """
                rows = await db_gateway.fetch_as_user(user_id, query, user_id, limit, offset)
                result_sessions: List[ConversationSession] = []
                for r in rows:
                    sid = r["session_id"]
                    session = await self.get_session_async(sid, user_id=user_id)
                    if session:
                        result_sessions.append(session)
                return result_sessions
            except Exception as e:
                logger.warning(f"Failed to query sessions from Neon PostgreSQL: {e}")
                if settings.requires_persistent_storage:
                    raise RuntimeError("Persistent session listing failed.") from e

        self._raise_if_persistence_unavailable()
        return self.list_sessions(user_id=user_id, limit=limit, offset=offset)

    async def delete_session(self, session_id: str, user_id: str = "default_user") -> bool:
        """Delete a conversation session and its messages. Authoritative when database is connected."""
        if session_id not in self._sessions and not db_gateway.is_connected:
            self._raise_if_persistence_unavailable()
            return False

        if db_gateway.is_connected:
            try:
                status = await db_gateway.execute_as_user(
                    user_id,
                    "DELETE FROM conversation_sessions WHERE session_id = $1",
                    session_id,
                )
                deleted = status != "DELETE 0"
            except Exception as exc:
                logger.exception("Failed to delete session messages from Neon PostgreSQL")
                raise RuntimeError(f"Database deletion failure: {exc}") from exc
        else:
            deleted = self._sessions.get(session_id) is not None

        self._sessions.pop(session_id, None)
        return deleted

    async def set_session_status(self, session_id: str, user_id: str, status: str) -> bool:
        """Persist a lifecycle transition for an already-owned conversation session."""
        if status not in {"created", "active", "ended"}:
            raise ValueError(f"Unsupported session status: {status}")
        if db_gateway.is_connected:
            query = """
            UPDATE conversation_sessions
            SET status = $3,
                updated_at = now(),
                ended_at = CASE WHEN $3 = 'ended' THEN now() ELSE ended_at END
            WHERE session_id = $1 AND user_id = $2
            """
            result = await db_gateway.execute_as_user(user_id, query, session_id, user_id, status)
            return result != "UPDATE 0"
        self._raise_if_persistence_unavailable()
        session = self._sessions.get(session_id)
        return bool(session and session.user_id == user_id)

    async def log_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str = "default_user",
        metadata: Optional[Dict] = None,
    ) -> ConversationMessage:
        """Append a message turn to the session with authoritative persistence."""
        msg = ConversationMessage(role=role, content=content, metadata=metadata or {})
        session = await self.create_session(session_id, user_id)

        if db_gateway.is_connected:
            try:
                query = """
                INSERT INTO messages (id, session_id, user_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """
                await db_gateway.execute_as_user(
                    user_id,
                    query,
                    msg.id,
                    session_id,
                    user_id,
                    role,
                    content,
                    metadata or {},
                    msg.timestamp,
                )
                await db_gateway.execute_as_user(
                    user_id,
                    "UPDATE conversation_sessions SET status = 'active', updated_at = now() WHERE session_id = $1",
                    session_id,
                )
            except Exception as exc:
                logger.exception("Failed to persist conversation message to Neon PostgreSQL")
                raise RuntimeError(f"Database persistence failure: {exc}") from exc

        # Only commit to in-memory session history after persistence succeeds
        session.messages.append(msg)
        logger.debug(f"[{session_id}] Logged message: turn_id={msg.id} role={role} chars={len(content)}")
        return msg


conversation_service = ConversationService()
