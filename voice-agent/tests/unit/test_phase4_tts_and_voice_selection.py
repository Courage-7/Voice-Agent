"""Unit tests for Phase 4: Aura to Flux TTS Migration & Dynamic Voice Selection."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.realtime.session import RealtimeClientSession
from app.voice.catalog import DEFAULT_VOICE_MODEL, voice_catalog_service


def test_voice_catalog_allowlist_validation():
    """Verify voice catalog validation and safe fallback behavior."""
    # 1. Exact match
    assert voice_catalog_service.validate_voice("aura-2-orion-en") == "aura-2-orion-en"

    # 2. Case-insensitive match
    assert voice_catalog_service.validate_voice("AURA-2-THALIA-EN") == "aura-2-thalia-en"

    # 3. Fuzzy search by name
    assert voice_catalog_service.validate_voice("thalia") == "aura-2-thalia-en"
    assert voice_catalog_service.validate_voice("perseus") == "aura-2-perseus-en"

    # 4. Unknown voice fallback
    assert voice_catalog_service.validate_voice("invalid-nonexistent-voice") == DEFAULT_VOICE_MODEL
    assert voice_catalog_service.validate_voice(None) == DEFAULT_VOICE_MODEL


def test_user_voice_preference_persistence():
    """Verify user voice preference saving and retrieval."""
    voice_catalog_service.set_user_voice("user_pref_test", "aura-2-arcas-en")
    assert voice_catalog_service.get_user_voice("user_pref_test") == "aura-2-arcas-en"


@pytest.mark.asyncio
async def test_deepgram_session_settings_with_active_voice():
    """Verify Settings configuration sends correct TTS speak model."""
    session = DeepgramVoiceAgentSession(
        session_id="sess_tts_test",
        user_id="user_tts",
        voice_model="aura-2-orion-en",
    )
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    await session._send_settings_configuration()
    assert mock_ws.send.called
    sent_payload = json.loads(mock_ws.send.call_args[0][0])

    assert sent_payload["type"] == "Settings"
    speak_cfg = sent_payload["agent"]["speak"]
    assert speak_cfg["provider"]["type"] == "deepgram"
    assert speak_cfg["provider"]["model"] == "aura-2-orion-en"


@pytest.mark.asyncio
async def test_deepgram_session_update_speak():
    """Verify update_speak sends UpdateSpeak message and updates internal model."""
    session = DeepgramVoiceAgentSession(
        session_id="sess_dyn_tts",
        user_id="user_dyn",
        voice_model="aura-2-thalia-en",
    )
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    await session.update_speak("aura-2-zeus-en")
    assert session.voice_model == "aura-2-zeus-en"
    assert mock_ws.send.called

    sent_payload = json.loads(mock_ws.send.call_args[0][0])
    assert sent_payload["type"] == "UpdateSpeak"
    assert sent_payload["speak"]["provider"]["model"] == "aura-2-zeus-en"


@pytest.mark.asyncio
async def test_realtime_client_session_handles_update_speak():
    """Verify RealtimeClientSession dispatches UpdateSpeak from client WS."""
    mock_client_ws = AsyncMock()
    session = RealtimeClientSession(
        session_id="sess_rt_tts",
        client_ws=mock_client_ws,
        user_id="user_rt",
    )
    session.deepgram_session.update_speak = AsyncMock()

    await session._handle_client_event({"type": "UpdateSpeak", "voice": "aura-2-perseus-en"})
    assert session.deepgram_session.update_speak.called
    assert session.deepgram_session.update_speak.call_args[0][0] == "aura-2-perseus-en"
