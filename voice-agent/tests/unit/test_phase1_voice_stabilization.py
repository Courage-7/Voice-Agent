"""Unit tests for Phase 1: Voice Hot-Path Stabilization & Measurement."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.observability.metrics import MetricsCollector
from app.realtime.session import RealtimeClientSession
from app.realtime.state import SessionState


@pytest.mark.asyncio
async def test_native_greeting_in_settings_configuration():
    """Verify that agent.greeting is populated natively in initial Settings payload."""
    session = DeepgramVoiceAgentSession(session_id="test_sess_1", user_id="user_123")
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    await session._send_settings_configuration()

    assert mock_ws.send.called
    sent_payload = json.loads(mock_ws.send.call_args[0][0])

    assert sent_payload["type"] == "Settings"
    assert "agent" in sent_payload
    assert sent_payload["agent"]["greeting"] == "Hello! I'm here and ready to help."
    assert sent_payload["agent"]["think"]["provider"]["type"] == "groq"
    assert sent_payload["agent"]["listen"]["provider"]["type"] == "deepgram"
    assert sent_payload["agent"]["speak"]["provider"]["type"] == "deepgram"


@pytest.mark.asyncio
async def test_settings_applied_does_not_send_duplicate_greeting():
    """Verify that SettingsApplied does not send an extra InjectAgentMessage."""
    session = DeepgramVoiceAgentSession(session_id="test_sess_2", user_id="user_123")
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    event = {"type": "SettingsApplied"}
    await session._handle_server_event(event)

    # Should not send any payload on websocket because native greeting handles startup
    assert not mock_ws.send.called


@pytest.mark.asyncio
async def test_latency_report_handling_safe_parsing():
    """Verify that LatencyReport events with partial/full fields are safely handled and forwarded."""
    forwarded_events = []

    async def mock_on_event(evt):
        forwarded_events.append(evt)

    session = DeepgramVoiceAgentSession(
        session_id="test_sess_3",
        user_id="user_123",
        on_event=mock_on_event,
    )
    session.ws = AsyncMock()
    session._is_running = True

    # Full report
    full_event = {
        "type": "LatencyReport",
        "stt_latency": 150.2,
        "ttt_token_latency": 210.5,
        "ttt_text_latency": 320.0,
        "ttt_tool_latency": 45.0,
        "tts_latency": 95.8,
        "total_latency": 780.0,
    }
    await session._handle_server_event(full_event)
    assert len(forwarded_events) == 1
    assert forwarded_events[0]["total_latency"] == 780.0

    # Minimal/partial report
    partial_event = {
        "type": "LatencyReport",
        "total_latency": 500.0,
    }
    await session._handle_server_event(partial_event)
    assert len(forwarded_events) == 2


def test_metrics_collector_session_and_turn_counters():
    """Verify MetricsCollector accurately tracks sessions and turns."""
    collector = MetricsCollector()
    assert collector.active_sessions == 0
    assert collector.total_turns == 0

    collector.increment_session()
    collector.increment_session()
    assert collector.active_sessions == 2

    collector.decrement_session()
    assert collector.active_sessions == 1

    collector.record_turn()
    collector.record_turn()
    assert collector.total_turns == 2

    collector.record_tool_call("send_email")
    assert collector.tool_calls_count.get("send_email") == 1

    prom_text = collector.export_prometheus_text()
    assert "voice_agent_active_sessions 1" in prom_text
    assert "voice_agent_total_turns 2" in prom_text
    assert 'voice_agent_tool_calls_total{tool="send_email"} 1' in prom_text


@pytest.mark.asyncio
async def test_realtime_client_session_wires_metrics_and_events():
    """Verify RealtimeClientSession tracks session lifecycle and turns via events."""
    mock_ws = AsyncMock()
    client_session = RealtimeClientSession(session_id="test_sess_4", client_ws=mock_ws)

    # Simulate start
    with patch.object(client_session.deepgram_session, "connect", return_value=True):
        await client_session.start()
        assert client_session.state == SessionState.LISTENING

    # Simulate agent turn completion
    await client_session._forward_event_to_client({"type": "AgentAudioDone"})
    assert client_session.state == SessionState.LISTENING

    # Simulate close
    await client_session.close()
    assert client_session.state == SessionState.DISCONNECTED
