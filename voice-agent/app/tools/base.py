from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    capability: str
    read_only: bool
    requires_confirmation: bool
    timeout_seconds: float
    input_schema: type[Any] | None = None
