"""Deepgram Voice Agent API WebSocket Session Manager."""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

import websockets
from app.agent.persona.service import persona_service
from app.conversations.service import conversation_service
from app.core.config import settings
from app.integrations.deepgram.function_calls import execute_function_calls
from app.integrations.deepgram.text import normalize_for_display, normalize_for_speech
from app.memory.service import memory_service
from app.observability.metrics import metrics_collector
from app.tools.capability import is_account_active, canonical_app_slug
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
        self._shutdown_task: Optional[asyncio.Task] = None
        self._tool_tasks: set[asyncio.Task] = set()
        self._function_tasks: Dict[str, asyncio.Task] = {}
        self._cancelled_function_calls: set[str] = set()
        self._is_running = False
        self._is_agent_speaking = False
        self._last_assistant_turn_interrupted = False

    async def connect(self) -> bool:
        """Establish WebSocket connection to Deepgram Voice Agent API."""
        if settings.demo_mode:
            return False
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
        """Send Settings immediately with base prompt, then enrich with memory context in background."""
        # ── Phase 1: Resolve cheap, synchronous values ────────────────────────
        user_context_str = f"User ID: {self.user_id}"

        # Base instructions with no memory (fast — no DB call)
        base_instructions = persona_service.get_voice_instructions(
            user_context=user_context_str,
            memory_context="",
        )

        # Greeting uses whatever profile name we might have cached; falls back gracefully
        greeting_text = self._generate_greeting(user_name=None)

        # Resolve active TTS voice
        active_voice = voice_catalog_service.validate_voice(
            self.voice_model or voice_catalog_service.get_user_voice(self.user_id, settings.deepgram_tts_model)
        )
        self.voice_model = active_voice

        # Resolve Groq model ID
        groq_model_name = settings.groq_model or "openai/gpt-oss-20b"
        groq_think_model = groq_model_name
        provider_type = (
            "open_ai"
            if (settings.groq_api_key or "/" in groq_think_model or "gpt" in groq_think_model
                or "oss" in groq_think_model or "llama" in groq_think_model)
            else "groq"
        )

        # Resolve STT listen provider
        # Flux uses v2 + EOT controls; Nova uses standard endpointing parameter
        is_flux = "flux" in (settings.deepgram_stt_model or "").lower()
        listen_provider: Dict[str, Any] = {
            "type": "deepgram",
            "model": settings.deepgram_stt_model,
        }
        if is_flux:
            listen_provider["version"] = "v2"
            if settings.deepgram_eot_threshold:
                listen_provider["eot_threshold"] = settings.deepgram_eot_threshold
            if settings.deepgram_eot_timeout_ms:
                listen_provider["eot_timeout_ms"] = settings.deepgram_eot_timeout_ms
        else:
            # endpointing: 500ms — prevents brief background noises (500ms silence required
            # before Deepgram commits the utterance to the LLM pipeline)
            listen_provider["endpointing"] = 500

        # Resolve and bind tools for the authenticated user's active accounts
        # before Settings is sent.  The background enrichment previously only
        # logged these schemas, leaving Deepgram with the empty initial binding.
        connected_app_slugs: list[str] = []
        active_caps = ["system", "memory"]
        try:
            from app.integrations.composio.client import composio_gateway
            accounts = await asyncio.wait_for(
                composio_gateway.get_connected_accounts(entity_id=self.user_id), timeout=2.0
            )
            for account in accounts:
                if not is_account_active(account.get("status", "")) or not account.get("is_active", True):
                    continue
                app_name = canonical_app_slug(account.get("app", ""))
                if not app_name:
                    continue
                connected_app_slugs.append(app_name)
                if app_name in ("GMAIL", "OUTLOOK"):
                    active_caps.append("email")
                if app_name in ("GOOGLECALENDAR", "OUTLOOK"):
                    active_caps.append("calendar")
                if app_name in ("SERPAPI", "PERPLEXITYAI", "TAVILY"):
                    active_caps.append("search")
                if app_name in ("GOOGLESHEETS", "GOOGLEDOCS", "GOOGLEDRIVE", "NOTION",
                                "MICROSOFT_TEAMS", "WHATSAPP", "TELEGRAM", "LINKEDIN",
                                "NEON", "I_LOVE_PDF"):
                    active_caps.append("workspace")
        except Exception as exc:
            logger.warning(f"[{self.session_id}] Could not resolve connected tools before Settings: {exc}")

        functions = tool_registry.get_deepgram_function_schemas(
            capabilities=list(set(active_caps)),
            connected_apps=connected_app_slugs,
        )

        think_payload: Dict[str, Any] = {
            "provider": {
                "type": provider_type,
                "model": groq_think_model,
                "temperature": settings.groq_temperature,
            },
            "prompt": base_instructions,
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
                "greeting": greeting_text,
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

        logger.info(
            f"[{self.session_id}] Sending Settings to Deepgram immediately "
            f"(voice='{active_voice}', model='{groq_think_model}', tools={len(functions)}, "
            f"endpointing={'eot_threshold/timeout' if is_flux else '500ms'})."
        )
        # ── Phase 1 complete: Settings sent — Deepgram starts immediately ─────
        await self.ws.send(json.dumps(config_payload))

        # ── Phase 2: Enrich prompt with user memory in background ─────────────
        # This runs after Settings is sent so it never blocks session startup.
        task = asyncio.create_task(
            self._enrich_prompt_async(
                active_voice=active_voice,
                groq_think_model=groq_think_model,
                provider_type=provider_type,
            )
        )
        self._tool_tasks.add(task)
        task.add_done_callback(self._tool_tasks.discard)

    async def _enrich_prompt_async(
        self,
        active_voice: str,
        groq_think_model: str,
        provider_type: str,
    ) -> None:
        """Background: fetch user profile + memories + connected apps, then UpdatePrompt."""
        try:
            async def _fetch_memories() -> str:
                try:
                    return await asyncio.wait_for(
                        memory_service.get_user_memory_summary(self.user_id, limit=5),
                        timeout=1.5,
                    )
                except Exception as e:
                    logger.warning(f"[{self.session_id}] Memory fetch skipped: {e}")
                    return ""

            async def _fetch_profile():
                try:
                    return await asyncio.wait_for(
                        user_service.get_or_create_user(self.user_id),
                        timeout=1.5,
                    )
                except Exception as e:
                    logger.warning(f"[{self.session_id}] Profile fetch skipped: {e}")
                    return None

            async def _fetch_accounts() -> list:
                try:
                    from app.integrations.composio.client import composio_gateway
                    return await asyncio.wait_for(
                        composio_gateway.get_connected_accounts(entity_id=self.user_id),
                        timeout=2.0,
                    )
                except Exception as e:
                    logger.warning(f"[{self.session_id}] Accounts fetch skipped: {e}")
                    return []

            memory_summary, profile, accounts = await asyncio.gather(
                _fetch_memories(),
                _fetch_profile(),
                _fetch_accounts(),
            )

            # Build enriched user context
            user_context_str = f"User ID: {self.user_id}"
            user_name: Optional[str] = None
            if profile and profile.full_name and profile.full_name not in ("User", "default_user"):
                user_name = profile.full_name.strip().split()[0]
                user_context_str = f"User Name: {profile.full_name}\nUser ID: {self.user_id}"

            # Resolve connected app capabilities for logging context
            connected_app_slugs: list[str] = []
            for acc in (accounts or []):
                if not is_account_active(acc.get("status", "")) or not acc.get("is_active", True):
                    continue
                app_name = canonical_app_slug(acc.get("app", ""))
                if app_name:
                    connected_app_slugs.append(app_name)

            enriched_instructions = persona_service.get_voice_instructions(
                user_context=user_context_str,
                memory_context=memory_summary,
            )

            # Send UpdatePrompt with enriched context mid-session
            # NOTE: Deepgram UpdatePrompt does NOT update function schemas —
            # tool schemas are locked at Settings time (Phase 1).
            if self.ws and self._is_running:
                update_payload = {
                    "type": "UpdatePrompt",
                    "prompt": enriched_instructions,
                }
                await self.ws.send(json.dumps(update_payload))
                logger.info(
                    f"[{self.session_id}] Prompt enriched: user='{user_name or 'anonymous'}', "
                    f"memory={'yes' if memory_summary else 'none'}, "
                    f"apps={connected_app_slugs or 'none'}, tools={len(functions)}."
                )

        except Exception:
            logger.exception(f"[{self.session_id}] _enrich_prompt_async failed silently.")


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

    def _generate_greeting(self, user_name: Optional[str] = None) -> str:
        """Generate a warm, casual, randomized greeting from a curated pool."""
        import random

        if user_name:
            greetings = [
                f"Hey {user_name}, good to have you back.",
                f"Hey {user_name}! What's on your mind?",
                f"Hi {user_name}, I'm listening.",
                f"Hey {user_name}, what can I help you with?",
                f"Good to hear from you, {user_name}. What's up?",
                f"Hey {user_name}! Ready when you are.",
                f"Hi there, {user_name}. What are we working on?",
                f"Hey {user_name}, go ahead whenever you're ready.",
            ]
        else:
            greetings = [
                "Hey, what's on your mind?",
                "Hi there! I'm listening.",
                "Hey! Go ahead whenever you're ready.",
                "Hi, how can I help?",
                "Hey there, what can I help you with?",
                "Hi! Ready when you are.",
                "Hey, what are we working on today?",
                "Hi, I'm here. What's up?",
            ]
        return random.choice(greetings)


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

        # Sanitize any ConversationText to eliminate emojis and markdown heading prefixes
        # Sanitize ConversationText and separate speech_text from display_markdown
        if event_type == "ConversationText":
            raw_content = event.get("content", "")
            if raw_content:
                speech_text = normalize_for_speech(raw_content)
                display_text = normalize_for_display(raw_content)
                event["content"] = speech_text
                event["speech_text"] = speech_text
                event["display_markdown"] = display_text

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

        # Forward event to Client WebSocket immediately if callback registered (F05 / Phase 5)
        if self.on_event:
            await self.on_event(event)

        # 2. Tool / Function Call Execution (Dispatched to tracked background worker so receive loop is never blocked)
        if event_type == "FunctionCallRequest":
            # Only execute calls the Voice Agent explicitly marks for the
            # client.  Server-side calls belong to Deepgram and do not receive
            # a client FunctionCallResponse.
            functions = event.get("functions", [])
            is_client_side = event.get("client_side") is True or any(
                isinstance(function, dict) and function.get("client_side") is True
                for function in functions
            )
            if not is_client_side:
                logger.warning("[%s] Ignoring non-client-side function call.", self.session_id)
                return
            call_ids = [str(fn.get("id") or "") for fn in functions if isinstance(fn, dict)]
            if not call_ids:
                call_ids = [str(event.get("function_call_id") or event.get("id") or "")]
            call_ids = [call_id for call_id in call_ids if call_id]
            if any(call_id in self._function_tasks for call_id in call_ids):
                logger.warning("[%s] Duplicate function request ignored: %s", self.session_id, call_ids)
                return
            task = asyncio.create_task(self._handle_function_call(event))
            for call_id in call_ids:
                self._function_tasks[call_id] = task
                task.add_done_callback(
                    lambda completed, key=call_id: self._function_tasks.pop(key, None)
                )
            self._tool_tasks.add(task)
            task.add_done_callback(self._tool_tasks.discard)

        elif event_type == "FunctionCallCancelled":
            cancelled_ids = event.get("function_call_ids") or [
                event.get("function_call_id") or event.get("id") or ""
            ]
            for raw_call_id in cancelled_ids:
                call_id = str(raw_call_id or "")
                if not call_id:
                    continue
                self._cancelled_function_calls.add(call_id)
                task = self._function_tasks.get(call_id)
                if task and not task.done():
                    task.cancel()
                logger.info("[%s] Function call cancelled: %s", self.session_id, call_id)

        # 3. Settings Applied -> Native greeting handles voice startup
        elif event_type == "SettingsApplied":
            logger.info(f"[{self.session_id}] Settings applied successfully by Deepgram Voice Agent.")

        # 4. Dynamic Speak / Voice Update Confirmation
        elif event_type == "SpeakUpdated":
            speak_data = event.get("speak") or event
            logger.info(f"[{self.session_id}] Deepgram SpeakUpdated confirmed: {speak_data}")

        # 5. Latency Telemetry Report (Normalize seconds to milliseconds - F06)
        elif event_type == "LatencyReport":
            stt = event.get("stt_latency")
            ttft = event.get("ttt_token_latency") or event.get("ttft")
            text_lat = event.get("ttt_text_latency")
            tool_lat = event.get("ttt_tool_latency")
            tts = event.get("tts_latency")
            total = event.get("total_latency")

            def to_ms(val: Optional[float]) -> Optional[float]:
                if val is None:
                    return None
                return round(val * 1000.0, 2) if val < 10.0 else round(val, 2)

            stt_ms = to_ms(stt)
            ttft_ms = to_ms(ttft)
            tts_ms = to_ms(tts)
            total_ms = to_ms(total)

            logger.info(
                f"[{self.session_id}] Deepgram LatencyReport: total={total_ms}ms, stt={stt_ms}ms, "
                f"ttft={ttft_ms}ms, text={to_ms(text_lat)}ms, tool={to_ms(tool_lat)}ms, tts={tts_ms}ms"
            )
            event["latency_ms"] = total_ms
            metrics_collector.record_latency(stt=stt_ms, ttft=ttft_ms, tts=tts_ms, total=total_ms)

        # 6. Warnings and Errors
        elif event_type == "Warning":
            msg = str(event.get("description") or event.get("message") or event)
            logger.warning(f"[{self.session_id}] Deepgram Warning event: {msg}")
            if "429" in msg or "rate_limit" in msg.lower():
                logger.warning(f"[{self.session_id}] Upstream think rate limit detected (429 TPM exhaustion).")
                if self.on_event:
                    await self.on_event({
                        "type": "Warning",
                        "code": "RATE_LIMIT_WARNING",
                        "message": "AI inference rate limit reached. Responses will resume in a few seconds.",
                        "raw_event": event,
                    })
        elif event_type == "Error":
            msg = str(event.get("description") or event.get("message") or event)
            logger.error(f"[{self.session_id}] Deepgram Error event: {msg}")
            if "FAILED_TO_THINK" in msg or "429" in msg or "rate_limit" in msg.lower():
                logger.error(f"[{self.session_id}] Deepgram think failed due to rate limits or inference error.")
                if self.on_event:
                    await self.on_event({
                        "type": "Error",
                        "code": "FAILED_TO_THINK_RATE_LIMIT",
                        "message": "AI inference capacity temporarily reached. Resuming shortly.",
                        "raw_event": event,
                    })

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

    async def _handle_function_call(self, event: Dict[str, Any]) -> None:
        """Delegate isolated execution mechanics to the function-call adapter."""
        await execute_function_calls(
            event,
            user_id=self.user_id,
            session_id=self.session_id,
            is_cancelled=lambda call_id: call_id in self._cancelled_function_calls,
            send_response=self._send_function_response,
            on_end_session=self._schedule_end_session,
        )

    async def _send_function_response(self, payload: Dict[str, Any]) -> None:
        """Write a function result only while the Deepgram socket is live."""
        if self.ws and self._is_running:
            await self.ws.send(json.dumps(payload))

    async def _schedule_end_session(self) -> None:
        """Allow the completion message to be spoken before closing the session."""
        if self._shutdown_task and not self._shutdown_task.done():
            return
        logger.info("[%s] End session requested by tool.", self.session_id)
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
        if self._shutdown_task and not self._shutdown_task.done():
            self._shutdown_task.cancel()
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        for t in list(self._tool_tasks):
            if not t.done():
                t.cancel()
        self._tool_tasks.clear()
        self._function_tasks.clear()
        self._cancelled_function_calls.clear()
        if self.ws:
            await self.ws.close()
        logger.info(f"[{self.session_id}] Deepgram session closed.")
