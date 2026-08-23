"""Prometheus and in-memory metrics collector."""

import logging
from typing import Dict
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects application-wide counters, gauges, and exports Prometheus format."""

    def __init__(self) -> None:
        self.active_sessions: int = 0
        self.total_turns: int = 0
        self.tool_calls_count: Dict[str, int] = {}

    def increment_session(self) -> None:
        self.active_sessions += 1

    def decrement_session(self) -> None:
        self.active_sessions = max(0, self.active_sessions - 1)

    def record_turn(self) -> None:
        self.total_turns += 1

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls_count[tool_name] = self.tool_calls_count.get(tool_name, 0) + 1

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

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()
