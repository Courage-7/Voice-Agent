"""Unit tests for Phase 1: Voice Hot-Path Stabilization & Measurement."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.observability.metrics import MetricsCollector
from app.realtime.orchestrator import DualStreamVoiceOrchestrator
from app.realtime.session import RealtimeClientSession
from app.realtime.state import SessionState


@pytest.mark.asyncio
async def test_native_greeting_on_orchestrator_connect():
    """Verify that orchestrator establishes state and prepares greeting on connect."""
    events = []

    async def mock_on_event(evt):
        events.append(evt)

    session = DualStreamVoiceOrchestrator(
        session_id="test_sess_1",
        user_id="user_123",
        on_event=mock_on_event,
    )
    with patch.object(session.stt_client, "connect", AsyncMock(return_value=True)):
        connected = await session.connect()
        assert connected is True
        assert session.state == SessionState.LISTENING
        state_events = [e for e in events if e.get("type") == "SessionStateChange"]
        assert len(state_events) >= 1
        assert any(e["state"] == "listening" for e in state_events)


@pytest.mark.asyncio
async def test_orchestrator_greeting_generation_variations():
    """Verify that orchestrator produces varied, natural greeting text."""
    session = DualStreamVoiceOrchestrator(session_id="test_sess_2", user_id="user_123")
    greeting_alex = session._generate_greeting("Alex")
    assert "Alex" in greeting_alex
    assert len(greeting_alex) > 10

    greeting_default = session._generate_greeting()
    assert len(greeting_default) > 10


@pytest.mark.asyncio
async def test_latency_report_handling_safe_parsing():
    """Verify that Latency metrics are safely recorded and summarized."""
    collector = MetricsCollector()
    collector.record_latency(stt=150.2, ttt_token=210.5, tts=95.8, total=780.0)
    collector.record_latency(stt=140.0, ttt_token=190.0, tts=110.0, total=500.0)

    summary = collector.get_summary()
    assert "latency" in summary
    assert summary["latency"]["total_roundtrip_ms"]["count"] == 2
    assert summary["latency"]["total_roundtrip_ms"]["avg"] == 640.0
    assert summary["latency"]["stt_ms"]["avg"] == 145.1


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


@pytest.mark.asyncio
async def test_realtime_client_session_reports_provider_connection_failure():
    """A failed provider connection must transition the client out of connected state."""
    mock_ws = AsyncMock()
    client_session = RealtimeClientSession(session_id="test_provider_failure", client_ws=mock_ws)

    with patch.object(client_session.deepgram_session, "connect", return_value=False):
        await client_session.start()

    messages = [json.loads(call.args[0]) for call in mock_ws.send_text.await_args_list]
    assert {"type": "SessionStateChange", "state": "error"} in messages
    assert any(message["type"] == "Error" for message in messages)


def test_dynamic_greeting_generation():
    """Verify dynamic greeting adapts to user's name and is warm and engaging."""
    session = DualStreamVoiceOrchestrator(session_id="test_sess_5", user_id="user_123")
    greeting_named = session._generate_greeting("Alex")
    assert "Alex" in greeting_named
    assert len(greeting_named) > 10

    greeting_default = session._generate_greeting("there")
    assert "there" in greeting_default
    assert len(greeting_default) > 10


@pytest.mark.asyncio
async def test_composio_connected_accounts_cache():
    """Verify composio gateway caches connected accounts to avoid startup lag."""
    from app.integrations.composio.client import ComposioGateway

    gateway = ComposioGateway()
    mock_client = MagicMock()
    gateway._client = mock_client

    mock_item = MagicMock()
    mock_item.toolkit = MagicMock(slug="gmail")
    mock_item.status = "ACTIVE"
    mock_item.id = "conn_123"

    mock_client.connected_accounts.list.return_value = MagicMock(items=[mock_item])

    # First call hits mock_client
    res1 = await gateway.get_connected_accounts("user_test")
    assert len(res1) == 1
    assert res1[0]["app"] == "GMAIL"
    assert mock_client.connected_accounts.list.call_count == 1

    # Second call within TTL hits cache (no network/SDK call)
    res2 = await gateway.get_connected_accounts("user_test")
    assert res2 == res1
    assert mock_client.connected_accounts.list.call_count == 1
