"""Unit tests for Phase 8: Advanced Turn-Taking & Telemetry Optimization."""

import asyncio
import json
from unittest.mock import AsyncMock
import pytest

from app.api.v1.system import health_check, telemetry_summary
from app.core.config import settings
from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.observability.metrics import metrics_collector


@pytest.mark.asyncio
async def test_deepgram_session_settings_includes_endpointing():
    """Verify Deepgram Settings payload includes data-driven endpointing configuration."""
    session = DeepgramVoiceAgentSession(
        session_id="sess_endpointing_test",
        user_id="user_eot",
    )
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    await session._send_settings_configuration()
    assert mock_ws.send.called
    sent_payload = json.loads(mock_ws.send.call_args[0][0])

    listen_cfg = sent_payload["agent"]["listen"]["provider"]
    assert listen_cfg["type"] == "deepgram"
    assert listen_cfg["model"] == settings.deepgram_stt_model


@pytest.mark.asyncio
async def test_latency_telemetry_recording_and_percentiles():
    """Verify LatencyReport event updates metrics collector and computes percentiles."""
    session = DeepgramVoiceAgentSession(
        session_id="sess_latency_test",
        user_id="user_lat",
    )

    # Ingest multiple latency reports
    samples = [
        {"type": "LatencyReport", "stt_latency": 150.0, "ttt_token_latency": 180.0, "tts_latency": 120.0, "total_latency": 450.0},
        {"type": "LatencyReport", "stt_latency": 140.0, "ttt_token_latency": 190.0, "tts_latency": 130.0, "total_latency": 460.0},
        {"type": "LatencyReport", "stt_latency": 160.0, "ttt_token_latency": 210.0, "tts_latency": 110.0, "total_latency": 480.0},
    ]

    for sample in samples:
        await session._handle_server_event(sample)

    summary = metrics_collector.get_summary()
    assert "latency" in summary
    assert summary["latency"]["total_roundtrip_ms"]["count"] >= 3
    assert summary["latency"]["total_roundtrip_ms"]["p50"] > 0
    assert summary["latency"]["stt_ms"]["avg"] > 0


@pytest.mark.asyncio
async def test_telemetry_endpoints_response_contracts():
    """Verify health and telemetry API endpoints return valid structured contracts."""
    health_res = await health_check()
    assert health_res["status"] == "healthy"
    assert "turn_taking" in health_res
    assert health_res["turn_taking"]["eot_threshold"] == settings.deepgram_eot_threshold

    summary_res = await telemetry_summary()
    assert "active_sessions" in summary_res
    assert "total_turns" in summary_res
    assert "latency" in summary_res
