"""Full-Duplex Decoupled Dual-Stream Voice & Display Realtime Orchestrator.

Orchestrates Deepgram Live STT, Groq LPU LLM reasoning with dual-stream formatting,
Deepgram Aura-2 / Flux streaming TTS, and real-time client WebSocket coordination.
Provides rich on-screen Markdown/KaTeX rendering without polluting spoken voice audio.
"""

import asyncio
import json
import logging
import re
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.agent.persona.service import persona_service
from app.agent.integration_actions import (
    execute_requested_integration_actions,
    format_integration_response,
)
from app.conversations.service import conversation_service
from app.core.config import settings
from app.integrations.deepgram.stt_client import DeepgramLiveSTTClient
from app.integrations.deepgram.tts_client import tts_client
from app.integrations.llm.client import groq_client
from app.memory.service import memory_service
from app.observability.metrics import metrics_collector
from app.realtime.state import SessionState
from app.users.service import user_service
from app.voice.catalog import voice_catalog_service

logger = logging.getLogger(__name__)

SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.?!])\s+')


class DualStreamVoiceOrchestrator:
    """Full-duplex orchestrator coordinating STT, dual-stream LLM, TTS, tools, and client."""

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
        self.voice_model = voice_catalog_service.validate_voice(voice_model or settings.deepgram_tts_model)
        self.on_audio_chunk = on_audio_chunk
        self.on_event = on_event

        self.state = SessionState.CONNECTING
        self._is_running = False
        self._is_agent_speaking = False
        self._active_turn_task: Optional[asyncio.Task] = None
        self._tool_tasks: set[asyncio.Task] = set()

        # Context caches
        self._user_context_str = f"User ID: {self.user_id}"
        self._user_name: Optional[str] = None
        self._memory_summary = ""
        # STT Client
        self.stt_client = DeepgramLiveSTTClient(
            session_id=session_id,
            model=settings.deepgram_stt_model,
            sample_rate=settings.input_sample_rate,
            endpointing_ms=settings.deepgram_eot_timeout_ms,
            on_transcript=self._handle_stt_transcript,
            on_speech_started=self._handle_barge_in,
            on_utterance_end=self._handle_stt_utterance_end,
            on_error=self._handle_stt_error,
        )

    async def connect(self) -> bool:
        """Establish connections and start orchestrator."""
        return await self.start()

    async def start(self) -> bool:
        """Start the orchestrator session, load user context, and connect to STT."""
        self._is_running = True
        self.state = SessionState.CONNECTED
        await self._send_event({"type": "SessionStateChange", "state": self.state.value})

        # Load only the context this orchestrator uses.  Tool eligibility is
        # resolved at execution time by the capability engine, never guessed
        # from a startup snapshot.
        await self._load_session_context()

        # Connect STT
        stt_connected = await self.stt_client.connect()
        if stt_connected:
            self.state = SessionState.LISTENING
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})

            # Send dynamic initial greeting
            greeting = self._generate_greeting(self._user_name)
            asyncio.create_task(self._deliver_assistant_greeting(greeting))
            return True
        else:
            self.state = SessionState.ERROR
            await self._send_event({
                "type": "Error",
                "message": "Speech recognition service could not be connected. Please verify DEEPGRAM_API_KEY.",
            })
            return False

    async def _load_session_context(self) -> None:
        """Load user profile and memory context concurrently."""
        async def _fetch_memories() -> str:
            try:
                return await asyncio.wait_for(memory_service.get_user_memory_summary(self.user_id, limit=5), timeout=0.8)
            except Exception as e:
                logger.warning(f"[{self.session_id}] Memory fetch timed out: {e}")
                return ""

        async def _fetch_profile():
            try:
                return await asyncio.wait_for(user_service.get_or_create_user(self.user_id), timeout=0.8)
            except Exception as e:
                logger.warning(f"[{self.session_id}] Profile fetch timed out: {e}")
                return None

        mem_res, profile_res = await asyncio.gather(
            _fetch_memories(),
            _fetch_profile(),
            return_exceptions=True,
        )

        if isinstance(mem_res, str):
            self._memory_summary = mem_res
        if profile_res and not isinstance(profile_res, Exception) and profile_res.full_name:
            if profile_res.full_name not in ("User", "default_user"):
                self._user_name = profile_res.full_name.strip().split()[0]
                self._user_context_str = f"User Name: {profile_res.full_name}\nUser ID: {self.user_id}"

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

    async def _deliver_assistant_greeting(self, greeting_text: str) -> None:
        """Speak and display the initial assistant greeting."""
        try:
            self._is_agent_speaking = True
            self.state = SessionState.SPEAKING
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})
            await self._send_event({"type": "AgentStartedSpeaking"})

            # Send display transcript
            await self._send_event({
                "type": "ConversationText",
                "role": "assistant",
                "content": greeting_text,
                "display_markdown": greeting_text,
                "speech_text": greeting_text,
            })

            # Stream audio to client
            async for audio_chunk in tts_client.stream_speech_audio(greeting_text, voice_model=self.voice_model):
                if not self._is_agent_speaking:
                    break
                if self.on_audio_chunk:
                    await self.on_audio_chunk(audio_chunk)

            self._is_agent_speaking = False
            self.state = SessionState.LISTENING
            await self._send_event({"type": "AgentAudioDone"})
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})
        except Exception as e:
            logger.debug(f"[{self.session_id}] Greeting audio stream closed: {e}")
            self._is_agent_speaking = False

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Forward raw 16kHz linear16 PCM from client mic to STT."""
        if self._is_running:
            await self.stt_client.send_audio(pcm_bytes)

    async def inject_user_message(self, text: str) -> None:
        """Inject user text input (typing in input box) and generate response."""
        clean_text = text.strip()
        if not clean_text:
            return
        await self._handle_user_turn(clean_text)

    async def _handle_stt_transcript(self, transcript: str, is_final: bool, speech_final: bool) -> None:
        """Handle incoming transcript from Deepgram Live STT."""
        if not transcript:
            return

        # Interim transcript updates subtitle immediately
        await self._send_event({
            "type": "ConversationText",
            "role": "user",
            "content": transcript,
            "is_final": is_final,
        })

        if speech_final:
            logger.info(f"[{self.session_id}] STT speech turn finalized: '{transcript}'")
            await self._handle_user_turn(transcript)

    async def _handle_barge_in(self) -> None:
        """Instantly interrupt assistant speech and cancel generation when user speaks."""
        if self._is_agent_speaking or (self._active_turn_task and not self._active_turn_task.done()):
            logger.info(f"[{self.session_id}] Barge-in triggered: interrupting active assistant turn.")
            self._is_agent_speaking = False
            if self._active_turn_task and not self._active_turn_task.done():
                self._active_turn_task.cancel()

            self.state = SessionState.USER_SPEAKING
            await self._send_event({"type": "AssistantInterrupted"})
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})

    async def _handle_stt_utterance_end(self) -> None:
        """STT detected end of speech."""
        logger.debug(f"[{self.session_id}] STT UtteranceEnd received.")

    async def _handle_stt_error(self, err: str) -> None:
        logger.error(f"[{self.session_id}] STT Error: {err}")

    async def _handle_user_turn(self, user_text: str) -> None:
        """Process finalized user turn: log to DB, generate dual-stream response, speak to TTS."""
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()

        # Log user message to Neon PostgreSQL under RLS
        await conversation_service.log_message(
            session_id=self.session_id,
            role="user",
            content=user_text,
            user_id=self.user_id,
        )

        self._active_turn_task = asyncio.create_task(self._process_turn_pipeline(user_text))

    async def _process_turn_pipeline(self, user_text: str) -> None:
        """Execute the complete LLM reasoning, dual-stream generation, tool execution, and TTS loop."""
        try:
            self.state = SessionState.THINKING
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})
            await self._send_event({"type": "AgentThinking"})

            # A connection lookup is only a precondition.  For a supported
            # integration request, execute every planned read action here before
            # generating a response so the model cannot stop after merely
            # reporting connected apps.
            integration_execution = await execute_requested_integration_actions(
                user_text=user_text,
                user_id=self.user_id,
                session_id=self.session_id,
                on_activity=self._send_event,
            )
            if integration_execution is not None:
                await self._deliver_completed_integration_turn(
                    format_integration_response(integration_execution)
                )
                return

            # Build system instructions
            instructions = persona_service.get_voice_instructions(
                user_context=self._user_context_str,
                memory_context=self._memory_summary,
            )

            # Fetch recent conversation messages
            session_obj = conversation_service.get_session(self.session_id)
            recent_msgs = []
            if session_obj and session_obj.messages:
                for m in session_obj.messages[-6:]:
                    recent_msgs.append({"role": m.role, "content": m.content})
            else:
                recent_msgs.append({"role": "user", "content": user_text})

            dual_prompt = (
                f"{instructions}\n\n"
                "### DUAL-STREAM VOICE & DISPLAY PROTOCOL\n"
                "Format your complete response using exactly two tagged blocks:\n"
                "<display>\n"
                "Rich GitHub-flavored markdown for on-screen rendering. Use clear headings (##), bold text, bullet points, "
                "tables, fenced code blocks with language tags, and KaTeX math formulas ($...$ for inline, $$...$$ for display equations).\n"
                "</display>\n"
                "<speech>\n"
                "Plain, natural, conversational spoken English. Speak only words a human would pronounce aloud. "
                "NEVER include asterisks, hash tags, backticks, LaTeX symbols, code, URLs, or markdown syntax here. "
                "Explain the intuition of mathematical formulas or code naturally without reading raw syntax.\n"
                "</speech>\n"
            )

            messages = [{"role": "system", "content": dual_prompt}] + recent_msgs

            def extract_tag(text: str, tag: str) -> str:
                start_tag = f"<{tag}>"
                end_tag = f"</{tag}>"
                if start_tag not in text:
                    return ""
                start_idx = text.find(start_tag) + len(start_tag)
                end_idx = text.find(end_tag)
                if end_idx != -1:
                    return text[start_idx:end_idx]
                return text[start_idx:]

            # Stream LLM tokens from Groq
            full_response_text = ""
            display_accumulated = ""
            speech_accumulated = ""
            speech_sentence_buffer = ""

            async for delta in groq_client.stream_chat_completion(messages=messages):
                full_response_text += delta

                current_display = extract_tag(full_response_text, "display")
                current_speech = extract_tag(full_response_text, "speech")

                # Stream display markdown updates to client
                if current_display and current_display != display_accumulated:
                    display_accumulated = current_display
                    await self._send_event({
                        "type": "ConversationText",
                        "role": "assistant",
                        "content": display_accumulated,
                        "display_markdown": display_accumulated,
                        "speech_text": current_speech,
                    })

                # Stream spoken sentences to TTS
                if len(current_speech) > len(speech_accumulated):
                    new_speech = current_speech[len(speech_accumulated):]
                    speech_accumulated = current_speech
                    speech_sentence_buffer += new_speech

                    if any(punct in speech_sentence_buffer for punct in (". ", "? ", "! ", ".\n", "?\n")):
                        parts = SENTENCE_SPLIT_REGEX.split(speech_sentence_buffer)
                        for sentence in parts[:-1]:
                            if sentence.strip():
                                await self._speak_sentence_chunk(sentence.strip())
                        speech_sentence_buffer = parts[-1]

            # Flush remaining speech buffer
            if speech_sentence_buffer.strip():
                await self._speak_sentence_chunk(speech_sentence_buffer.strip())

            # Fallback if model didn't use tags at all
            if not display_accumulated and full_response_text.strip():
                display_accumulated = full_response_text.strip()
            if not speech_accumulated and full_response_text.strip():
                speech_accumulated = re.sub(r'[*#`$_\\]', '', full_response_text).strip()
                await self._speak_sentence_chunk(speech_accumulated)

            # Finalize assistant turn
            self.state = SessionState.LISTENING
            self._is_agent_speaking = False
            await self._send_event({"type": "AgentAudioDone"})
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})
            metrics_collector.record_turn()

            # Persist to Neon PostgreSQL with both display_markdown and speech_text
            await conversation_service.log_message(
                session_id=self.session_id,
                role="assistant",
                content=display_accumulated,
                user_id=self.user_id,
                metadata={
                    "display_markdown": display_accumulated,
                    "speech_text": speech_accumulated,
                },
            )

        except asyncio.CancelledError:
            logger.info(f"[{self.session_id}] Assistant turn generation cancelled by user barge-in.")
            self._is_agent_speaking = False
            self.state = SessionState.LISTENING
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})
        except Exception as e:
            logger.exception(f"[{self.session_id}] Error in turn pipeline: {e}")
            self.state = SessionState.LISTENING
            self._is_agent_speaking = False
            await self._send_event({"type": "AgentAudioDone"})
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})

    async def _deliver_completed_integration_turn(self, response_text: str) -> None:
        """Display, speak, and persist an already-executed integration result."""
        await self._send_event({
            "type": "ConversationText",
            "role": "assistant",
            "content": response_text,
            "display_markdown": response_text,
            "speech_text": response_text,
        })
        await self._speak_sentence_chunk(response_text)
        self.state = SessionState.LISTENING
        self._is_agent_speaking = False
        await self._send_event({"type": "AgentAudioDone"})
        await self._send_event({"type": "SessionStateChange", "state": self.state.value})
        metrics_collector.record_turn()
        await conversation_service.log_message(
            session_id=self.session_id,
            role="assistant",
            content=response_text,
            user_id=self.user_id,
            metadata={"display_markdown": response_text, "speech_text": response_text},
        )

    async def _speak_sentence_chunk(self, sentence: str) -> None:
        """Stream a single spoken sentence through TTS and send audio frames to client."""
        if not sentence or not self._is_running:
            return

        clean_sentence = re.sub(r'[*#`$_\\]', '', sentence).strip()
        if not clean_sentence:
            return

        if not self._is_agent_speaking:
            self._is_agent_speaking = True
            self.state = SessionState.SPEAKING
            await self._send_event({"type": "SessionStateChange", "state": self.state.value})
            await self._send_event({"type": "AgentStartedSpeaking"})

        try:
            async for audio_chunk in tts_client.stream_speech_audio(clean_sentence, voice_model=self.voice_model):
                if not self._is_agent_speaking:
                    # User barged in mid-sentence
                    break
                if self.on_audio_chunk:
                    await self.on_audio_chunk(audio_chunk)
        except asyncio.CancelledError:
            logger.debug(f"[{self.session_id}] Audio chunk streaming cancelled.")
            raise

    async def update_prompt(self, new_instructions: str) -> None:
        """Update system prompt dynamically mid-session."""
        self._memory_summary += f"\nUser Directive: {new_instructions}"

    async def update_speak(self, voice_model: str) -> None:
        """Update TTS voice model dynamically mid-session."""
        validated = voice_catalog_service.validate_voice(voice_model)
        self.voice_model = validated
        voice_catalog_service.set_user_voice(self.user_id, validated)
        await self._send_event({
            "type": "SpeakUpdated",
            "voice": validated,
        })

    async def _send_event(self, event: Dict[str, Any]) -> None:
        """Send JSON control/transcript event to client WebSocket."""
        if self.on_event:
            await self.on_event(event)

    async def close(self) -> None:
        """Clean up all active orchestrator tasks and connections."""
        self._is_running = False
        self._is_agent_speaking = False

        tasks_to_cancel = []
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()
            tasks_to_cancel.append(self._active_turn_task)

        for t in list(self._tool_tasks):
            if not t.done():
                t.cancel()
                tasks_to_cancel.append(t)

        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        await self.stt_client.close()
        self.state = SessionState.DISCONNECTED
        logger.info(f"[{self.session_id}] Dual-Stream Voice Orchestrator closed.")
