"""Conversation recording and logging service."""

import logging
from typing import Dict, List, Optional

from app.conversations.models import ConversationMessage, ConversationSession
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
        """Get or initialize a conversation session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id, user_id=user_id)
            self._prune_sessions_if_needed()
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a session by session ID from memory cache."""
        return self._sessions.get(session_id)

    async def get_session_async(self, session_id: str, user_id: Optional[str] = None) -> Optional[ConversationSession]:
        """Retrieve a session by session ID, hydrating from Neon PostgreSQL if not in memory."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        if db_gateway.is_connected:
            try:
                if not user_id:
                    return None
                rows = await db_gateway.fetch_as_user(
                    user_id,
                    "SELECT id, session_id, user_id, role, content, metadata, created_at FROM messages WHERE session_id = $1 ORDER BY created_at ASC",
                    session_id,
                )
                if rows:
                    user_id = rows[0]["user_id"] or "default_user"
                    session = ConversationSession(session_id=session_id, user_id=user_id)
                    for r in rows:
                        row_dict = dict(r)
                        session.messages.append(
                            ConversationMessage(
                                id=row_dict.get("id"),
                                role=row_dict.get("role", "user"),
                                content=row_dict.get("content", ""),
                                metadata=row_dict.get("metadata") or {},
                            )
                        )
                    self._sessions[session_id] = session
                    self._prune_sessions_if_needed()
                    return session
            except Exception as e:
                logger.warning(f"Failed to fetch session {session_id} from Neon PostgreSQL: {e}")

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
                SELECT 
                    session_id,
                    user_id,
                    MIN(created_at) as created_at,
                    COUNT(*) as msg_count
                FROM messages
                WHERE user_id = $1
                GROUP BY session_id, user_id
                ORDER BY MIN(created_at) DESC
                LIMIT $2 OFFSET $3
                """
                rows = await db_gateway.fetch_as_user(user_id, query, user_id, limit, offset)
                result_sessions: List[ConversationSession] = []
                for r in rows:
                    sid = r["session_id"]
                    if sid in self._sessions and self._sessions[sid].messages:
                        result_sessions.append(self._sessions[sid])
                    else:
                        msg_rows = await db_gateway.fetch_as_user(
                            user_id,
                            "SELECT id, session_id, user_id, role, content, metadata, created_at FROM messages WHERE session_id = $1 ORDER BY created_at ASC",
                            sid,
                        )
                        sess = ConversationSession(
                            session_id=sid,
                            user_id=r["user_id"] or user_id,
                            created_at=r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                        )
                        for mr in msg_rows:
                            sess.messages.append(
                                ConversationMessage(
                                    id=mr.get("id"),
                                    role=mr.get("role", "user"),
                                    content=mr.get("content", ""),
                                    metadata=mr.get("metadata") or {},
                                    timestamp=mr.get("created_at"),
                                )
                            )
                        self._sessions[sid] = sess
                        result_sessions.append(sess)

                for sid, s in self._sessions.items():
                    if s.user_id == user_id and not any(rs.session_id == sid for rs in result_sessions):
                        result_sessions.append(s)

                result_sessions.sort(key=lambda s: str(s.created_at), reverse=True)
                return result_sessions[:limit]
            except Exception as e:
                logger.warning(f"Failed to query sessions from Neon PostgreSQL: {e}")

        return self.list_sessions(user_id=user_id, limit=limit, offset=offset)

    async def delete_session(self, session_id: str, user_id: str = "default_user") -> bool:
        """Delete a conversation session and its messages. Authoritative when database is connected."""
        if session_id not in self._sessions and not db_gateway.is_connected:
            return False

        if db_gateway.is_connected:
            try:
                await db_gateway.execute_as_user(user_id, "DELETE FROM messages WHERE session_id = $1", session_id)
            except Exception as exc:
                logger.exception("Failed to delete session messages from Neon PostgreSQL")
                raise RuntimeError(f"Database deletion failure: {exc}") from exc

        deleted = self._sessions.pop(session_id, None) is not None
        return deleted or bool(db_gateway.is_connected)

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
            except Exception as exc:
                logger.exception("Failed to persist conversation message to Neon PostgreSQL")
                raise RuntimeError(f"Database persistence failure: {exc}") from exc

        # Only commit to in-memory session history after persistence succeeds
        session = self.get_or_create_session(session_id, user_id)
        session.messages.append(msg)
        logger.debug(f"[{session_id}] Logged message: turn_id={msg.id} role={role} chars={len(content)}")
        return msg


conversation_service = ConversationService()
