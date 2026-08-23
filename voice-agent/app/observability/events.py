"""Structured telemetry events."""

from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """Structured telemetry record."""

    event_type: str
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)
