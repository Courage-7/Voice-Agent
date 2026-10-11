"""Deepgram integration package for Live STT and Streaming Aura-2 TTS."""

from app.integrations.deepgram.stt_client import DeepgramLiveSTTClient
from app.integrations.deepgram.tts_client import DeepgramStreamingTTSClient, tts_client
from app.integrations.deepgram.text import normalize_for_display, normalize_for_speech

__all__ = [
    "DeepgramLiveSTTClient",
    "DeepgramStreamingTTSClient",
    "tts_client",
    "normalize_for_display",
    "normalize_for_speech",
]
