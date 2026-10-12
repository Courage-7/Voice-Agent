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
from app.users.service import user_service
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

    # A durable session must exist before the WebSocket is admitted.  The
    # user row is created first because conversation_sessions has an owner FK.
    await user_service.get_or_create_user(
        user_id,
        full_name=current_user.full_name or "User",
        email=current_user.email or None,
    )

    # Set user voice preference if provided
    selected_voice = None
    if payload.voice_model:
        selected_voice = voice_catalog_service.set_user_voice(user_id, payload.voice_model)

    await conversation_service.create_session(
        session_id,
        user_id,
        persona=payload.persona,
        voice_model=selected_voice,
    )

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
    conv = await conversation_service.get_session_async(session_id, user_id=current_user.id)
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
    active_session = _active_sessions.get(session_id)
    if active_session and active_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: session belongs to another user.")

    conv = await conversation_service.get_session_async(session_id, user_id=current_user.id)
    if conv and conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: session belongs to another user.")

    if not active_session and not conv:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if active_session:
        _active_sessions.pop(session_id, None)
        await active_session.close()
        await conversation_service.set_session_status(session_id, current_user.id, "ended")
        logger.info(f"Voice session ended via API: {session_id}")
        return {"success": True, "session_id": session_id, "status": "ended"}

    if conv:
        await conversation_service.set_session_status(session_id, current_user.id, "ended")
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

    # 3. Hydrate through the authenticated user's RLS scope before accepting.
    # The in-memory cache is intentionally bounded and is empty after a
    # restart, so it cannot be the authority for session ownership.
    conv = await conversation_service.get_session_async(session_id, user_id=user.id)
    if not conv or conv.user_id != user.id:
        logger.warning(f"Rejected WebSocket for unknown or unowned session '{session_id}' (caller={user.id})")
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

    try:
        await conversation_service.set_session_status(session_id, user.id, "active")
        await session.start(subprotocol="shinra-auth" if ws_token else None)

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
        try:
            await conversation_service.set_session_status(session_id, user.id, "ended")
        except Exception:
            logger.warning("Failed to persist WebSocket close for session %s", session_id)
