"""Voice session lifecycle and WebSocket streaming endpoints with authenticated identity validation."""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from app.auth.models import AuthUser
from app.conversations.service import conversation_service
from app.core.dependencies import get_current_user, is_allowed_origin, validate_ws_auth
from app.realtime.session import RealtimeClientSession
from app.voice.catalog import voice_catalog_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Track active voice sessions
_active_sessions: dict[str, RealtimeClientSession] = {}


class CreateSessionRequest(BaseModel):
    persona: str = "companion"
    voice_model: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    voice_model: Optional[str] = None
    message_count: int = 0


@router.get("/voices")
@router.get("/catalog")
async def get_voice_catalog():
    """List all available Deepgram Flux and Aura-2 TTS voices with metadata."""
    return {"success": True, "voices": voice_catalog_service.get_catalog()}


@router.post(
    "/sessions",
    response_model=SessionResponse,
)
async def create_voice_session(
    payload: CreateSessionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Create a new voice session bound to the authenticated caller's identity."""
    session_id = str(uuid4())
    user_id = current_user.id

    # Pre-register the conversation session under verified owner
    conversation_service.get_or_create_session(session_id, user_id)

    # Set user voice preference if provided
    selected_voice = None
    if payload.voice_model:
        selected_voice = voice_catalog_service.set_user_voice(user_id, payload.voice_model)

    logger.info(f"Voice session created: {session_id} for verified user {user_id} (voice: {selected_voice})")
    return SessionResponse(
        session_id=session_id,
        user_id=user_id,
        voice_model=selected_voice,
        status="created",
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    responses={
        403: {"description": "Access denied: session belongs to another user."},
        404: {"description": "Voice session not found."},
    },
)
async def get_voice_session(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Inspect an owned voice session's current state and message count."""
    conv = conversation_service.get_session(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: session belongs to another user.")

    active = session_id in _active_sessions
    status_str = _active_sessions[session_id].state.value if active else "inactive"
    voice_model = _active_sessions[session_id].voice_model if active else None

    return SessionResponse(
        session_id=session_id,
        user_id=conv.user_id,
        voice_model=voice_model,
        status=status_str,
        message_count=len(conv.messages),
    )


@router.post(
    "/sessions/{session_id}/end",
    responses={
        403: {"description": "Access denied: session belongs to another user."},
        404: {"description": "Voice session not found."},
    },
)
async def end_voice_session(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Gracefully end an active voice session if owned by caller."""
    conv = conversation_service.get_session(session_id)
    if conv and conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: session belongs to another user.")

    active_session = _active_sessions.pop(session_id, None)
    if active_session:
        await active_session.close()
        logger.info(f"Voice session ended via API: {session_id}")
        return {"success": True, "session_id": session_id, "status": "ended"}

    if conv:
        return {"success": True, "session_id": session_id, "status": "already_inactive"}

    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")


@router.websocket("/ws/{session_id}")
async def voice_agent_websocket(
    websocket: WebSocket,
    session_id: str,
    voice: Optional[str] = Query(default=None),
) -> None:
    """Full-duplex WebSocket connection authenticated by Clerk subprotocol."""
    # 1. Validate Origin header (Finding F01/F07)
    origin = websocket.headers.get("origin")
    if not is_allowed_origin(origin):
        logger.warning(f"Rejected WebSocket: unauthorized origin '{origin}'")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Browser WebSockets cannot send Authorization. Carry the Clerk token in
    # a negotiated subprotocol, never a URL query parameter.
    subprotocols = websocket.scope.get("subprotocols") or []
    ws_token = subprotocols[1] if len(subprotocols) == 2 and subprotocols[0] == "shinra-auth" else None
    try:
        user = validate_ws_auth(websocket, token=ws_token)
    except Exception as e:
        logger.warning(f"WebSocket auth failed for session {session_id}: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3. Enforce session ownership
    conv = conversation_service.get_session(session_id)
    if conv and conv.user_id and conv.user_id != user.id:
        logger.warning(f"Session ownership mismatch: session '{session_id}' owned by '{conv.user_id}', caller is '{user.id}'")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    logger.info(f"WebSocket accepted: session_id={session_id}, user_id={user.id}, voice={voice}")

    session = RealtimeClientSession(
        session_id=session_id,
        client_ws=websocket,
        user_id=user.id,
        voice_model=voice,
    )
    _active_sessions[session_id] = session

    await session.start(subprotocol="shinra-auth" if ws_token else None)

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
