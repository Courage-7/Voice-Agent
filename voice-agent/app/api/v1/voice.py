"""Voice session lifecycle and WebSocket streaming endpoints."""

import json
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from app.conversations.service import conversation_service
from app.realtime.session import RealtimeClientSession

logger = logging.getLogger(__name__)
router = APIRouter()

# Track active voice sessions
_active_sessions: dict[str, RealtimeClientSession] = {}


class CreateSessionRequest(BaseModel):
    user_id: str = "default_user"
    persona: str = "executive"


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    message_count: int = 0


@router.post(
    "/sessions",
    response_model=SessionResponse,
)
async def create_voice_session(payload: CreateSessionRequest):
    """Create a new voice session and return the session ID for WebSocket connection."""
    session_id = str(uuid4())

    # Pre-register the conversation session so it exists before WS connect
    conversation_service.get_or_create_session(session_id, payload.user_id)

    logger.info(f"Voice session created: {session_id} for user {payload.user_id}")
    return SessionResponse(
        session_id=session_id,
        user_id=payload.user_id,
        status="created",
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    responses={404: {"description": "Voice session not found."}},
)
async def get_voice_session(session_id: str):
    """Inspect a voice session's current state and message count."""
    conv = conversation_service.get_session(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    active = session_id in _active_sessions
    status = _active_sessions[session_id].state.value if active else "inactive"

    return SessionResponse(
        session_id=session_id,
        user_id=conv.user_id,
        status=status,
        message_count=len(conv.messages),
    )


@router.post(
    "/sessions/{session_id}/end",
    responses={404: {"description": "Voice session not found."}},
)
async def end_voice_session(session_id: str):
    """Gracefully end an active voice session, closing Deepgram and archiving transcript."""
    active_session = _active_sessions.pop(session_id, None)
    if active_session:
        await active_session.close()
        logger.info(f"Voice session ended via API: {session_id}")
        return {"success": True, "session_id": session_id, "status": "ended"}

    # Session exists in conversation history but not actively streaming
    conv = conversation_service.get_session(session_id)
    if conv:
        return {"success": True, "session_id": session_id, "status": "already_inactive"}

    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")


@router.websocket("/ws/{session_id}")
async def voice_agent_websocket(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(default="default_user"),
) -> None:
    """Full-duplex WebSocket connection for streaming audio and voice agent events."""
    logger.info(f"WebSocket connection request: session_id={session_id}, user_id={user_id}")

    session = RealtimeClientSession(session_id=session_id, client_ws=websocket, user_id=user_id)
    _active_sessions[session_id] = session

    await session.start()

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                await session.handle_client_message(message["bytes"])
            elif "text" in message and message["text"]:
                await session.handle_client_message(message["text"])

    except (WebSocketDisconnect, RuntimeError):
        logger.info(f"Client disconnected: session_id={session_id}")
    except Exception:
        logger.exception(f"Error in WebSocket handler: session_id={session_id}")
    finally:
        _active_sessions.pop(session_id, None)
        await session.close()
