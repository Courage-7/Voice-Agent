"""Realtime Client Session orchestrator connecting Client WebSocket with Deepgram Gateway."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket
from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.realtime.state import SessionState

logger = logging.getLogger(__name__)


class RealtimeClientSession:
    """Coordinates full-duplex streaming between the Client WebSocket and Deepgram Agent."""

    def __init__(self, session_id: str, client_ws: WebSocket, user_id: str = "default_user") -> None:
        self.session_id = session_id
        self.client_ws = client_ws
        self.user_id = user_id
        self.state = SessionState.CONNECTING

        # Backend Deepgram Session
        self.deepgram_session = DeepgramVoiceAgentSession(
            session_id=session_id,
            user_id=user_id,
            on_audio_chunk=self._forward_audio_to_client,
            on_event=self._forward_event_to_client,
        )

    async def start(self) -> None:
        """Start the session and connect to Deepgram."""
        await self.client_ws.accept()
        self.state = SessionState.CONNECTED
        await self._send_state_update()

        connected = await self.deepgram_session.connect()
        if connected:
            self.state = SessionState.LISTENING
            await self._send_state_update()
        else:
            self.state = SessionState.ERROR
            await self._send_json_message({
                "type": "Error",
                "message": "Deepgram Voice Agent could not be connected. Check DEEPGRAM_API_KEY.",
            })

    async def handle_client_message(self, message: Any) -> None:
        """Handle incoming binary audio or JSON message from Client."""
        if isinstance(message, bytes):
            # Forward mic audio directly to Deepgram
            await self.deepgram_session.send_audio(message)
        elif isinstance(message, str):
            try:
                event = json.loads(message)
                await self._handle_client_event(event)
            except Exception:
                logger.exception(f"[{self.session_id}] Error parsing client message")

    async def _handle_client_event(self, event: Dict[str, Any]) -> None:
        """Handle control messages from client UI."""
        event_type = event.get("type", "")
        if event_type == "InjectUserMessage":
            text = event.get("content") or event.get("message") or ""
            if text:
                await self.deepgram_session.inject_user_message(text)
        elif event_type == "UpdatePrompt":
            prompt = event.get("prompt", "")
            if prompt:
                await self.deepgram_session.update_prompt(prompt)

    async def _forward_audio_to_client(self, audio_chunk: bytes) -> None:
        """Stream raw synthesized audio frame to client speaker."""
        try:
            await self.client_ws.send_bytes(audio_chunk)
        except Exception as e:
            logger.debug(f"[{self.session_id}] Failed to send audio chunk to client: {e}")

    async def _forward_event_to_client(self, event: Dict[str, Any]) -> None:
        """Stream JSON control event / transcript to client UI."""
        event_type = event.get("type", "")
        if event_type == "UserStartedSpeaking":
            self.state = SessionState.USER_SPEAKING
        elif event_type == "AgentThinking":
            self.state = SessionState.THINKING
        elif event_type == "AgentStartedSpeaking":
            self.state = SessionState.SPEAKING
        elif event_type == "AgentAudioDone":
            self.state = SessionState.LISTENING

        await self._send_json_message(event)

    async def _send_json_message(self, data: Dict[str, Any]) -> None:
        try:
            await self.client_ws.send_text(json.dumps(data))
        except Exception as e:
            logger.debug(f"[{self.session_id}] Failed to send JSON to client: {e}")

    async def _send_state_update(self) -> None:
        await self._send_json_message({"type": "SessionStateChange", "state": self.state.value})

    async def close(self) -> None:
        """Clean up on client disconnect."""
        self.state = SessionState.DISCONNECTED
        await self.deepgram_session.close()
        logger.info(f"[{self.session_id}] Realtime Client Session ended.")
