"""Unit tests for Phase 8: Advanced Turn-Taking & Telemetry Optimization."""

import asyncio
import json
from unittest.mock import AsyncMock
import pytest

from app.api.v1.system import health_check, telemetry_summary
from app.core.config import settings
from app.observability.metrics import metrics_collector
from app.realtime.orchestrator import DualStreamVoiceOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_initializes_with_configured_endpointing():
    """Verify orchestrator STT client is initialized with configured endpointing and model."""
    session = DualStreamVoiceOrchestrator(
        session_id="sess_endpointing_test",
        user_id="user_eot",
    )
    assert session.stt_client.endpointing_ms == settings.deepgram_eot_timeout_ms
    assert session.stt_client.model == settings.deepgram_stt_model


@pytest.mark.asyncio
async def test_latency_telemetry_recording_and_percentiles():
    """Verify latency reports update metrics collector and compute percentiles."""
    metrics_collector.record_latency(stt=150.0, ttt_token=180.0, tts=120.0, total=450.0)
    metrics_collector.record_latency(stt=140.0, ttt_token=190.0, tts=130.0, total=460.0)
    metrics_collector.record_latency(stt=160.0, ttt_token=210.0, tts=110.0, total=480.0)

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
