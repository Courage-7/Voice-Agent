"""Deepgram Voice Agent API WebSocket Session Manager."""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

import websockets
from app.agent.persona.service import persona_service
from app.conversations.service import conversation_service
from app.core.config import settings
from app.memory.service import memory_service
from app.observability.metrics import metrics_collector
from app.tools.registry import tool_registry
from app.users.service import user_service
from app.voice.catalog import voice_catalog_service

logger = logging.getLogger(__name__)


class DeepgramVoiceAgentSession:
    """Manages a single live Voice Agent session with Deepgram Agent WebSocket API."""

    def __init__(
        self,
        session_id: str,
        user_id: str = "default_user",
        voice_model: Optional[str] = None,
        on_audio_chunk: Optional[Callable[[bytes], Coroutine[Any, Any, None]]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.voice_model = voice_model
        self.on_audio_chunk = on_audio_chunk
        self.on_event = on_event

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._is_agent_speaking = False
        self._last_assistant_turn_interrupted = False

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
        """Send the initial Settings payload specifying Groq + Nova-2 + Flux/Aura-2 TTS + Memory + Tools."""
        # 1. Fetch user context & bounded memories safely
        memory_summary = ""
        user_context_str = f"User ID: {self.user_id}"
        try:
            memory_summary = await memory_service.get_user_memory_summary(self.user_id, limit=5)
        except Exception as e:
            logger.warning(f"[{self.session_id}] Could not fetch user memory summary: {e}")

        try:
            profile = await user_service.get_or_create_user(self.user_id)
            if profile and profile.full_name and profile.full_name != "User":
                user_context_str = f"User Name: {profile.full_name}\nUser ID: {self.user_id}"
        except Exception as e:
            logger.warning(f"[{self.session_id}] Could not fetch user profile: {e}")

        instructions = persona_service.get_voice_instructions(
            user_context=user_context_str,
            memory_context=memory_summary,
        )
        functions = tool_registry.get_deepgram_function_schemas()

        # Resolve active TTS voice (respecting session override, user preference, or system default)
        active_voice = voice_catalog_service.validate_voice(
            self.voice_model or voice_catalog_service.get_user_voice(self.user_id, settings.deepgram_tts_model)
        )
        self.voice_model = active_voice

        # Resolve Groq model ID for Deepgram Voice Agent think provider
        groq_model_name = settings.groq_model
        if "compound" in groq_model_name.lower() or not groq_model_name:
            groq_think_model = "llama-3.3-70b-versatile"
        elif groq_model_name.startswith("groq/"):
            groq_think_model = groq_model_name.replace("groq/", "")
        else:
            groq_think_model = groq_model_name

        listen_provider: Dict[str, Any] = {
            "type": "deepgram",
            "model": settings.deepgram_stt_model,
        }
        if "flux" in settings.deepgram_stt_model.lower():
            listen_provider["eot_threshold"] = settings.deepgram_eot_threshold
            listen_provider["eot_timeout_ms"] = settings.deepgram_eot_timeout_ms

        think_payload: Dict[str, Any] = {
            "provider": {
                "type": "groq",
                "model": groq_think_model,
                "temperature": settings.groq_temperature,
            },
            "prompt": instructions,
            "functions": functions,
        }
        if settings.groq_api_key:
            think_payload["endpoint"] = {
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "headers": {
                    "Authorization": f"Bearer {settings.groq_api_key}",
                },
            }

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
                "greeting": "Hello! I'm here and ready to help.",
                "listen": {
                    "provider": listen_provider,
                },
                "think": think_payload,
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": active_voice,
                    }
                },
            },
        }

        think_cfg = config_payload["agent"]["think"]
        logger.info(
            f"[{self.session_id}] Sending Settings to Deepgram (TTS voice '{active_voice}', Groq model '{groq_think_model}', {len(functions)} tools, endpointing={settings.deepgram_eot_threshold}/{settings.deepgram_eot_timeout_ms}ms)."
        )
        logger.info(
            f"[{self.session_id}] Deepgram Think configuration: provider.type={think_cfg.get('provider', {}).get('type')}, "
            f"provider.model={think_cfg.get('provider', {}).get('model')}, endpoint={think_cfg.get('provider', {}).get('endpoint', 'DEFAULT')}, "
            f"functions_count={len(functions)}"
        )
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

    async def update_speak(self, voice_model: str) -> None:
        """Dynamically update agent voice model mid-session."""
        validated = voice_catalog_service.validate_voice(voice_model)
        self.voice_model = validated
        voice_catalog_service.set_user_voice(self.user_id, validated)

        if self.ws and self._is_running:
            payload = {
                "type": "UpdateSpeak",
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": validated,
                    }
                },
            }
            logger.info(f"[{self.session_id}] Sending UpdateSpeak to Deepgram with voice '{validated}'")
            await self.ws.send(json.dumps(payload))

    async def _receive_loop(self) -> None:
        """Continuous receive loop for Deepgram audio frames and JSON control messages."""
        try:
            async for message in self.ws:
                if isinstance(message, bytes):
                    # Audio chunk from Deepgram Aura/Flux TTS
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

        # 1. Track Agent Speaking State for Interruption Detection
        if event_type == "AgentStartedSpeaking":
            self._is_agent_speaking = True
            self._last_assistant_turn_interrupted = False
        elif event_type == "AgentAudioDone":
            self._is_agent_speaking = False
        elif event_type == "UserStartedSpeaking":
            if self._is_agent_speaking:
                self._last_assistant_turn_interrupted = True
                self._is_agent_speaking = False
                logger.info(f"[{self.session_id}] User interrupted agent speech turn.")

        # 2. Tool / Function Call Execution
        if event_type == "FunctionCallRequest":
            await self._handle_function_call(event)

        # 3. Settings Applied -> Native greeting handles voice startup
        elif event_type == "SettingsApplied":
            logger.info(f"[{self.session_id}] Settings applied successfully by Deepgram Voice Agent.")

        # 4. Dynamic Speak / Voice Update Confirmation
        elif event_type == "SpeakUpdated":
            speak_data = event.get("speak") or event
            logger.info(f"[{self.session_id}] Deepgram SpeakUpdated confirmed: {speak_data}")

        # 5. Latency Telemetry Report
        elif event_type == "LatencyReport":
            stt = event.get("stt_latency")
            ttft = event.get("ttt_token_latency") or event.get("ttft")
            text_lat = event.get("ttt_text_latency")
            tool_lat = event.get("ttt_tool_latency")
            tts = event.get("tts_latency")
            total = event.get("total_latency")
            logger.info(
                f"[{self.session_id}] Deepgram LatencyReport: total={total}ms, stt={stt}ms, "
                f"ttft={ttft}ms, text={text_lat}ms, tool={tool_lat}ms, tts={tts}ms"
            )
            metrics_collector.record_latency(stt=stt, ttft=ttft, tts=tts, total=total)

        # 6. Warnings and Errors
        elif event_type == "Warning":
            logger.warning(f"[{self.session_id}] Deepgram Warning event: {event.get('message') or event}")
        elif event_type == "Error":
            logger.error(f"[{self.session_id}] Deepgram Error event: {event.get('message') or event}")

        # 7. Conversation Transcript Logging with Interruption Metadata
        elif event_type == "ConversationText":
            role = event.get("role", "assistant")
            content = event.get("content", "")
            if content:
                meta: Dict[str, Any] = {}
                if role == "assistant" and self._last_assistant_turn_interrupted:
                    meta["interrupted"] = True
                    self._last_assistant_turn_interrupted = False
                await conversation_service.log_message(
                    session_id=self.session_id,
                    role=role,
                    content=content,
                    user_id=self.user_id,
                    metadata=meta,
                )

        # 8. Forward event to Client WebSocket if callback registered
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


