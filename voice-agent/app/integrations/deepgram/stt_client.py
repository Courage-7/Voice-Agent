"""Deepgram Live Streaming STT (Speech-to-Text) WebSocket Client.

Provides full-duplex live transcription using Deepgram Nova-2 with real-time
interim results, endpointing, and instant speech detection for barge-in.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, Optional
from urllib.parse import urlencode

import websockets
from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepgramLiveSTTClient:
    """Manages real-time streaming audio transcription via Deepgram Nova-2 WebSocket."""

    def __init__(
        self,
        session_id: str,
        model: Optional[str] = None,
        sample_rate: int = 16000,
        endpointing_ms: int = 350,
        on_transcript: Optional[Callable[[str, bool, bool], Coroutine[Any, Any, None]]] = None,
        on_speech_started: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        on_utterance_end: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        on_error: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self.session_id = session_id
        self.model = model or settings.deepgram_stt_model or "nova-2"
        self.sample_rate = sample_rate
        self.endpointing_ms = endpointing_ms

        self.on_transcript = on_transcript
        self.on_speech_started = on_speech_started
        self.on_utterance_end = on_utterance_end
        self.on_error = on_error

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def connect(self) -> bool:
        """Establish streaming WebSocket connection to Deepgram STT."""
        if not settings.deepgram_api_key:
            logger.warning(f"[{self.session_id}] DEEPGRAM_API_KEY is not configured for STT.")
            return False

        params = {
            "model": self.model,
            "encoding": "linear16",
            "sample_rate": str(self.sample_rate),
            "channels": "1",
            "smart_format": "true",
            "interim_results": "true",
            "endpointing": str(self.endpointing_ms),
            "vad_events": "true",
        }
        url = f"wss://api.deepgram.com/v1/listen?{urlencode(params)}"
        headers = {"Authorization": f"Token {settings.deepgram_api_key}"}

        try:
            logger.info(f"[{self.session_id}] Connecting to Deepgram Live STT ({self.model})...")
            self.ws = await websockets.connect(url, additional_headers=headers)
            self._is_running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info(f"[{self.session_id}] Deepgram Live STT connected.")
            return True
        except Exception as e:
            logger.exception(f"[{self.session_id}] Failed to connect to Deepgram Live STT: {e}")
            self._is_running = False
            return False

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Forward raw 16kHz linear16 PCM audio frame to Deepgram STT."""
        if self.ws and self._is_running:
            try:
                await self.ws.send(pcm_bytes)
            except Exception as e:
                logger.debug(f"[{self.session_id}] Error sending audio to Deepgram STT: {e}")

    async def _receive_loop(self) -> None:
        """Receive transcripts and VAD control messages from Deepgram."""
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    data = json.loads(message)
                    await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[{self.session_id}] Deepgram STT connection closed.")
        except Exception:
            logger.exception(f"[{self.session_id}] Error in Deepgram STT receive loop")
        finally:
            self._is_running = False

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Process incoming Deepgram STT event."""
        msg_type = data.get("type", "")

        # 1. Speech activity started (Crucial for Instant Barge-in)
        if msg_type == "SpeechStarted" or data.get("speech_started"):
            logger.debug(f"[{self.session_id}] STT detected SpeechStarted")
            if self.on_speech_started:
                await self.on_speech_started()
            return

        # 2. Utterance end (User finished a phrase / silence threshold reached)
        if msg_type == "UtteranceEnd":
            logger.debug(f"[{self.session_id}] STT detected UtteranceEnd")
            if self.on_utterance_end:
                await self.on_utterance_end()
            return

        # 3. Transcription result
        channel = data.get("channel", {})
        alternatives = channel.get("alternatives", [])
        if alternatives:
            transcript = alternatives[0].get("transcript", "").strip()
            is_final = data.get("is_final", False)
            speech_final = data.get("speech_final", False)

            if transcript and self.on_transcript:
                await self.on_transcript(transcript, is_final, speech_final)

        # 4. Error notification
        if msg_type == "Error" or "error" in data:
            err_msg = data.get("message") or data.get("error") or "STT Error"
            logger.error(f"[{self.session_id}] Deepgram STT error: {err_msg}")
            if self.on_error:
                await self.on_error(str(err_msg))

    async def close(self) -> None:
        """Gracefully terminate STT WebSocket session."""
        self._is_running = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                # Send Deepgram close stream frame
                await self.ws.send(json.dumps({"type": "CloseStream"}))
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        logger.info(f"[{self.session_id}] Deepgram Live STT closed.")

