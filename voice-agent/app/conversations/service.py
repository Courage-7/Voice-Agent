"""Conversation recording and logging service."""

import asyncio
import logging
from typing import Dict, List, Optional

from app.conversations.models import ConversationMessage, ConversationSession
from app.integrations.supabase.client import supabase_gateway

logger = logging.getLogger(__name__)


class ConversationService:
    """Service to track live session turns and archive history to Supabase."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, session_id: str, user_id: str = "default_user") -> ConversationSession:
        """Get or initialize a conversation session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id, user_id=user_id)
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a session by session ID."""
        return self._sessions.get(session_id)

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

    async def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session and its messages."""
        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]

        if supabase_gateway.is_connected:
            try:
                await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("messages")
                    .delete().eq("session_id", session_id).execute()
                )
            except Exception:
                logger.exception("Failed to delete session messages from Supabase")

        return True

    async def log_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str = "default_user",
        metadata: Optional[Dict] = None,
    ) -> ConversationMessage:
        """Append a message turn to the session."""
        session = self.get_or_create_session(session_id, user_id)
        msg = ConversationMessage(role=role, content=content, metadata=metadata or {})
        session.messages.append(msg)

        logger.debug(f"[{session_id}] Logged {role}: {content[:60]}...")

        if supabase_gateway.is_connected:
            try:
                row = {
                    "id": msg.id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "created_at": msg.timestamp.isoformat(),
                }
                await asyncio.to_thread(
                    lambda: supabase_gateway.client.table("messages").insert(row).execute()
                )
            except Exception as e:
                logger.debug(f"Supabase messages table unavailable ({e}); maintaining in-memory session history.")

        return msg


conversation_service = ConversationService()
