"""Deepgram Voice Agent API WebSocket Session Manager."""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

import websockets
from app.agent.persona.service import persona_service
from app.conversations.service import conversation_service
from app.core.config import settings
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class DeepgramVoiceAgentSession:
    """Manages a single live Voice Agent session with Deepgram Agent WebSocket API."""

    def __init__(
        self,
        session_id: str,
        user_id: str = "default_user",
        on_audio_chunk: Optional[Callable[[bytes], Coroutine[Any, Any, None]]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.on_audio_chunk = on_audio_chunk
        self.on_event = on_event

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def connect(self) -> bool:
        """Establish WebSocket connection to Deepgram Voice Agent API."""
        if not settings.deepgram_api_key:
            logger.warning(f"[{self.session_id}] DEEPGRAM_API_KEY is not configured. Running in mock voice mode.")
            return False

        headers = {"Authorization": f"Token {settings.deepgram_api_key}"}
        url = settings.deepgram_agent_ws_url

        try:
            logger.info(f"[{self.session_id}] Connecting to Deepgram Voice Agent at {url}...")
            self.ws = await websockets.connect(url, additional_headers=headers)
            self._is_running = True

            # Send Initial Settings Configuration
            await self._send_settings_configuration()

            # Start listening loop
            self._listen_task = asyncio.create_task(self._receive_loop())
            logger.info(f"[{self.session_id}] Deepgram Voice Agent session established successfully.")
            return True

        except Exception:
            logger.exception(f"[{self.session_id}] Failed to connect to Deepgram Voice Agent")
            self._is_running = False
            return False

    async def _send_settings_configuration(self) -> None:
        """Send the initial Settings payload specifying Groq + Nova-2 + Aura + Tools."""
        instructions = persona_service.get_voice_instructions(user_context=f"User ID: {self.user_id}")
        functions = tool_registry.get_deepgram_function_schemas()

        # Groq model supported by Deepgram Voice Agent API think provider
        groq_think_model = "openai/gpt-oss-20b"

        config_payload = {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": settings.input_sample_rate,
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": settings.output_sample_rate,
                },
            },
            "agent": {
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.deepgram_stt_model,
                    }
                },
                "think": {
                    "provider": {
                        "type": "groq",
                        "model": groq_think_model,
                    },
                    "prompt": instructions,
                    "functions": functions,
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.deepgram_tts_model,
                    }
                },
            },
        }

        logger.info(f"[{self.session_id}] Sending Settings to Deepgram (Groq model '{groq_think_model}', {len(functions)} tools).")
        await self.ws.send(json.dumps(config_payload))

    async def send_audio(self, audio_data: bytes) -> None:
        """Forward raw client PCM audio bytes to Deepgram."""
        if self.ws and self._is_running:
            try:
                await self.ws.send(audio_data)
            except Exception:
                pass

    async def inject_user_message(self, message: str) -> None:
        """Inject user message text into the live agent conversation."""
        if self.ws and self._is_running:
            payload = {"type": "InjectUserMessage", "content": message}
            await self.ws.send(json.dumps(payload))

    async def update_prompt(self, new_instructions: str) -> None:
        """Dynamically update agent system instructions mid-session."""
        if self.ws and self._is_running:
            payload = {"type": "UpdatePrompt", "prompt": new_instructions}
            await self.ws.send(json.dumps(payload))

    async def _receive_loop(self) -> None:
        """Continuous receive loop for Deepgram audio frames and JSON control messages."""
        try:
            async for message in self.ws:
                if isinstance(message, bytes):
                    # Audio chunk from Deepgram Aura TTS
                    if self.on_audio_chunk:
                        await self.on_audio_chunk(message)
                else:
                    # JSON event message
                    event = json.loads(message)
                    await self._handle_server_event(event)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[{self.session_id}] Deepgram WebSocket connection closed.")
        except Exception:
            logger.exception(f"[{self.session_id}] Error in Deepgram receive loop")
        finally:
            self._is_running = False

    async def _handle_server_event(self, event: Dict[str, Any]) -> None:
        """Handle control events from Deepgram."""
        event_type = event.get("type", "Unknown")
        logger.debug(f"[{self.session_id}] Received Deepgram event: {event_type}")

        # 1. Tool / Function Call Execution
        if event_type == "FunctionCallRequest":
            await self._handle_function_call(event)

        # 2. Settings Applied -> Trigger Instant Spoken Greeting
        elif event_type == "SettingsApplied":
            logger.info(f"[{self.session_id}] Settings applied. Triggering instant spoken greeting.")
            greeting_payload = {
                "type": "InjectAgentMessage",
                "content": "Hello! I'm here and ready to help.",
            }
            if self.ws and self._is_running:
                await self.ws.send(json.dumps(greeting_payload))

        # 3. Conversation Transcript Logging
        elif event_type == "ConversationText":
            role = event.get("role", "assistant")
            content = event.get("content", "")
            if content:
                await conversation_service.log_message(
                    session_id=self.session_id,
                    role=role,
                    content=content,
                    user_id=self.user_id,
                )

        # 4. Forward event to Client WebSocket if callback registered
        if self.on_event:
            await self.on_event(event)

    async def _handle_function_call(self, event: Dict[str, Any]) -> None:
        """Execute tools and send FunctionCallResponse back to Deepgram."""
        functions_to_call = event.get("functions", [])
        if not functions_to_call:
            call_id = event.get("function_call_id") or event.get("id") or ""
            tool_name = event.get("function_name") or event.get("name") or ""
            params_raw = event.get("input") or event.get("arguments") or {}
            functions_to_call = [{"id": call_id, "name": tool_name, "arguments": params_raw}]

        for fn in functions_to_call:
            call_id = fn.get("id", "")
            tool_name = fn.get("name", "")
            params_raw = fn.get("arguments", {})

            if isinstance(params_raw, str):
                try:
                    params = json.loads(params_raw)
                except Exception:
                    params = {"query": params_raw}
            else:
                params = params_raw or {}

            logger.info(f"[{self.session_id}] Executing tool '{tool_name}' (call_id: {call_id})...")

            tool_result = await tool_registry.execute_tool(
                tool_name=tool_name,
                arguments=params,
                user_id=self.user_id,
                session_id=self.session_id,
            )

            response_payload = {
                "type": "FunctionCallResponse",
                "id": call_id,
                "name": tool_name,
                "content": json.dumps(tool_result),
            }
            logger.info(f"[{self.session_id}] Sending FunctionCallResponse for '{tool_name}'...")
            if self.ws:
                await self.ws.send(json.dumps(response_payload))

            if tool_result.get("end_session"):
                logger.info(f"[{self.session_id}] End session requested by tool. Scheduling session shutdown.")
                self._shutdown_task = asyncio.create_task(self._delayed_close(delay_seconds=3.0))

    async def _delayed_close(self, delay_seconds: float = 3.0) -> None:
        """Wait for parting speech synthesis to complete and then close session."""
        await asyncio.sleep(delay_seconds)
        if self.on_event:
            await self.on_event({"type": "SessionStateChange", "state": "DISCONNECTED"})
        await self.close()

    async def close(self) -> None:
        """Gracefully close session and cancel tasks."""
        self._is_running = False
        if self._listen_task:
            self._listen_task.cancel()
        if self.ws:
            await self.ws.close()
        logger.info(f"[{self.session_id}] Deepgram session closed.")


