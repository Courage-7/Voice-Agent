"""Prometheus and in-memory metrics collector with latency percentiles."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects application-wide counters, gauges, latency samples, and exports telemetry."""

    def __init__(self) -> None:
        self.active_sessions: int = 0
        self.total_turns: int = 0
        self.tool_calls_count: Dict[str, int] = {}
        self.stt_latencies: List[float] = []
        self.ttft_latencies: List[float] = []
        self.tts_latencies: List[float] = []
        self.total_latencies: List[float] = []

    def increment_session(self) -> None:
        self.active_sessions += 1

    def decrement_session(self) -> None:
        self.active_sessions = max(0, self.active_sessions - 1)

    def record_turn(self) -> None:
        self.total_turns += 1

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls_count[tool_name] = self.tool_calls_count.get(tool_name, 0) + 1

    def record_latency(
        self,
        stt: Optional[float] = None,
        ttft: Optional[float] = None,
        tts: Optional[float] = None,
        total: Optional[float] = None,
    ) -> None:
        """Record latency data points from live telemetry reports."""
        if stt is not None and stt > 0:
            self.stt_latencies.append(stt)
            if len(self.stt_latencies) > 1000:
                self.stt_latencies = self.stt_latencies[-500:]

        if ttft is not None and ttft > 0:
            self.ttft_latencies.append(ttft)
            if len(self.ttft_latencies) > 1000:
                self.ttft_latencies = self.ttft_latencies[-500:]

        if tts is not None and tts > 0:
            self.tts_latencies.append(tts)
            if len(self.tts_latencies) > 1000:
                self.tts_latencies = self.tts_latencies[-500:]

        if total is not None and total > 0:
            self.total_latencies.append(total)
            if len(self.total_latencies) > 1000:
                self.total_latencies = self.total_latencies[-500:]

    def _calc_percentiles(self, samples: List[float]) -> Dict[str, float]:
        if not samples:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "count": 0}
        s = sorted(samples)
        n = len(s)
        p50 = s[int(n * 0.50)]
        p95 = s[min(int(n * 0.95), n - 1)]
        p99 = s[min(int(n * 0.99), n - 1)]
        avg = sum(s) / n
        return {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "avg": round(avg, 2),
            "count": n,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get structured telemetry summary for dashboard and health inspection."""
        return {
            "active_sessions": self.active_sessions,
            "total_turns": self.total_turns,
            "tool_calls": self.tool_calls_count,
            "latency": {
                "stt_ms": self._calc_percentiles(self.stt_latencies),
                "ttft_ms": self._calc_percentiles(self.ttft_latencies),
                "tts_ms": self._calc_percentiles(self.tts_latencies),
                "total_roundtrip_ms": self._calc_percentiles(self.total_latencies),
            },
        }

    def export_prometheus_text(self) -> str:
        """Generate Prometheus exposition format text."""
        lines = [
            "# HELP voice_agent_active_sessions Number of active live WebSocket connections",
            "# TYPE voice_agent_active_sessions gauge",
            f"voice_agent_active_sessions {self.active_sessions}",
            "",
            "# HELP voice_agent_total_turns Total conversational turns processed",
            "# TYPE voice_agent_total_turns counter",
            f"voice_agent_total_turns {self.total_turns}",
            "",
            "# HELP voice_agent_tool_calls_total Total tool calls executed by name",
            "# TYPE voice_agent_tool_calls_total counter",
        ]
        for tool, count in self.tool_calls_count.items():
            lines.append(f'voice_agent_tool_calls_total{{tool="{tool}"}} {count}')

        # Latency metrics
        total_p50 = self._calc_percentiles(self.total_latencies)["p50"]
        lines.append("")
        lines.append("# HELP voice_agent_roundtrip_latency_p50_ms Round-trip latency p50 in milliseconds")
        lines.append("# TYPE voice_agent_roundtrip_latency_p50_ms gauge")
        lines.append(f"voice_agent_roundtrip_latency_p50_ms {total_p50}")

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()
