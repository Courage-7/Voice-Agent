"""Telemetry and latency measurement."""

import time
from typing import Dict, Optional
from pydantic import BaseModel, Field


class TurnLatencyMetrics(BaseModel):
    """Tracks latency milestones for a single conversational turn."""

    turn_id: str
    session_id: str
    stt_latency_ms: Optional[float] = None
    ttft_ms: Optional[float] = None  # Time-to-first-token
    ttfa_ms: Optional[float] = None  # Time-to-first-audio
    tool_duration_ms: Optional[float] = None
    total_turn_ms: Optional[float] = None


class LatencyTracker:
    """Helper to record milestone durations."""

    def __init__(self, session_id: str, turn_id: str):
        self.session_id = session_id
        self.turn_id = turn_id
        self._start_time = time.perf_counter()
        self.metrics = TurnLatencyMetrics(turn_id=turn_id, session_id=session_id)

    def record_ttft(self) -> None:
        self.metrics.ttft_ms = (time.perf_counter() - self._start_time) * 1000

    def record_ttfa(self) -> None:
        self.metrics.ttfa_ms = (time.perf_counter() - self._start_time) * 1000

    def finalize(self) -> TurnLatencyMetrics:
        self.metrics.total_turn_ms = (time.perf_counter() - self._start_time) * 1000
        return self.metrics
