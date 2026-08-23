"""Shared type definitions and data structures."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AudioConfig(BaseModel):
    """Configuration for input or output audio."""

    encoding: str = "linear16"
    sample_rate: int = 16000
    channels: int = 1


class ToolCallPayload(BaseModel):
    """Tool invocation payload."""

    call_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
