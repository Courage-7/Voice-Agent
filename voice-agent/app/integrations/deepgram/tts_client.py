"""Deepgram Streaming TTS (Text-to-Speech) Client.

Streams linear16 24kHz audio chunks directly from Deepgram Aura-2 / Flux TTS
endpoints with sub-200ms latency for real-time conversational voice delivery.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional
from urllib.parse import urlencode

import httpx
from app.core.config import settings
from app.voice.catalog import voice_catalog_service

logger = logging.getLogger(__name__)


class DeepgramStreamingTTSClient:
    """Streams synthesized audio frames from Deepgram Aura-2 / Flux TTS API."""

    def __init__(
        self,
        default_voice: Optional[str] = None,
        sample_rate: int = 24000,
    ) -> None:
        self.default_voice = default_voice or settings.deepgram_tts_model or "aura-2-thalia-en"
        self.sample_rate = sample_rate
        self._http_client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=3.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._http_client

    async def stream_speech_audio(
        self,
        text: str,
        voice_model: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Stream raw linear16 24kHz PCM chunks for a given text phrase."""
        clean_text = text.strip()
        if not clean_text:
            return

        active_voice = voice_catalog_service.validate_voice(
            voice_model or self.default_voice
        )
        if not settings.deepgram_api_key:
            logger.warning("DEEPGRAM_API_KEY not configured. Skipping TTS audio generation.")
            return

        client = self._get_client()
        params = {
            "model": active_voice,
            "encoding": "linear16",
            "sample_rate": str(self.sample_rate),
            "container": "none",
        }
        url = f"https://api.deepgram.com/v1/speak?{urlencode(params)}"
        headers = {
            "Authorization": f"Token {settings.deepgram_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"text": clean_text}

        try:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    logger.error(
                        f"Deepgram TTS returned HTTP {response.status_code}: {err_body.decode('utf-8', errors='ignore')}"
                    )
                    return

                # Stream raw PCM audio in 2KB–4KB chunks for smooth playback jitter buffering
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if chunk:
                        yield chunk

        except asyncio.CancelledError:
            logger.debug(f"TTS stream cancelled mid-utterance for: '{clean_text[:30]}...'")
            raise
        except Exception:
            logger.exception(f"Error streaming Deepgram TTS for text: '{clean_text[:40]}...'")

    async def synthesize(
        self,
        text: str,
        voice_model: Optional[str] = None,
    ) -> bytes:
        """Synthesize entire phrase to a single PCM byte string."""
        buffer = bytearray()
        try:
            async for chunk in self.stream_speech_audio(text, voice_model=voice_model):
                buffer.extend(chunk)
            return bytes(buffer)
        except Exception:
            logger.exception("Error in complete TTS synthesis")
            return b""

    async def close(self) -> None:
        """Close underlying HTTP connection pool."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None


tts_client = DeepgramStreamingTTSClient()

