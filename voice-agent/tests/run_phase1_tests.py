"""Standalone test runner for Phase 1 tests."""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.observability.metrics import MetricsCollector
from app.realtime.session import RealtimeClientSession
from app.realtime.state import SessionState


async def run_tests():
    passed = 0
    failed = 0

    print("Running Phase 1 Test Suite...\n")

    # Test 1: Native greeting in Settings configuration
    try:
        session = DeepgramVoiceAgentSession(session_id="test_sess_1", user_id="user_123")
        mock_ws = AsyncMock()
        session.ws = mock_ws
        session._is_running = True

        await session._send_settings_configuration()

        assert mock_ws.send.called, "mock_ws.send should have been called"
        sent_payload = json.loads(mock_ws.send.call_args[0][0])

        assert sent_payload["type"] == "Settings", f"Expected 'Settings', got {sent_payload['type']}"
        assert "agent" in sent_payload, "Missing 'agent' in payload"
        assert sent_payload["agent"]["greeting"] == "Hello! I'm here and ready to help.", f"Unexpected greeting: {sent_payload['agent'].get('greeting')}"
        assert sent_payload["agent"]["think"]["provider"]["type"] == "groq"
        assert sent_payload["agent"]["listen"]["provider"]["type"] == "deepgram"
        assert sent_payload["agent"]["speak"]["provider"]["type"] == "deepgram"
        print("  [PASS] test_native_greeting_in_settings_configuration")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_native_greeting_in_settings_configuration: {e}")
        failed += 1

    # Test 2: SettingsApplied does not send extra greeting
    try:
        session = DeepgramVoiceAgentSession(session_id="test_sess_2", user_id="user_123")
        mock_ws = AsyncMock()
        session.ws = mock_ws
        session._is_running = True

        event = {"type": "SettingsApplied"}
        await session._handle_server_event(event)

        assert not mock_ws.send.called, "mock_ws.send should NOT be called on SettingsApplied"
        print("  [PASS] test_settings_applied_does_not_send_duplicate_greeting")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_settings_applied_does_not_send_duplicate_greeting: {e}")
        failed += 1

    # Test 3: LatencyReport handling and safe parsing
    try:
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

        partial_event = {
            "type": "LatencyReport",
            "total_latency": 500.0,
        }
        await session._handle_server_event(partial_event)
        assert len(forwarded_events) == 2
        print("  [PASS] test_latency_report_handling_safe_parsing")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_latency_report_handling_safe_parsing: {e}")
        failed += 1

    # Test 4: MetricsCollector
    try:
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
        print("  [PASS] test_metrics_collector_session_and_turn_counters")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_metrics_collector_session_and_turn_counters: {e}")
        failed += 1

    # Test 5: RealtimeClientSession wiring
    try:
        mock_ws = AsyncMock()
        client_session = RealtimeClientSession(session_id="test_sess_4", client_ws=mock_ws)

        with patch.object(client_session.deepgram_session, "connect", return_value=True):
            await client_session.start()
            assert client_session.state == SessionState.LISTENING

        await client_session._forward_event_to_client({"type": "AgentAudioDone"})
        assert client_session.state == SessionState.LISTENING

        await client_session.close()
        assert client_session.state == SessionState.DISCONNECTED
        print("  [PASS] test_realtime_client_session_wires_metrics_and_events")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_realtime_client_session_wires_metrics_and_events: {e}")
        failed += 1

    print(f"\nPhase 1 Results: {passed} passed, {failed} failed.")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
