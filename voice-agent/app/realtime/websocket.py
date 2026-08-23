"""FastAPI WebSocket endpoint for real-time voice streaming."""

import logging
from uuid import uuid4

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from app.realtime.session import RealtimeClientSession

logger = logging.getLogger(__name__)
ws_router = APIRouter()


@ws_router.websocket("/ws/agent")
async def voice_agent_websocket(
    websocket: WebSocket,
    user_id: str = Query(default="default_user"),
    session_id: str = Query(default_factory=lambda: str(uuid4())),
) -> None:
    """Full-duplex WebSocket connection for streaming audio and voice agent events."""
    logger.info(f"New client WebSocket connection request: session_id={session_id}, user_id={user_id}")
    session = RealtimeClientSession(session_id=session_id, client_ws=websocket, user_id=user_id)

    await session.start()

    try:
        while True:
            # Receive either binary audio frames or JSON control text
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                await session.handle_client_message(message["bytes"])
            elif "text" in message and message["text"]:
                await session.handle_client_message(message["text"])

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket: session_id={session_id}")
    except Exception:
        logger.exception(f"Error in client WebSocket handler: session_id={session_id}")
    finally:
        await session.close()
