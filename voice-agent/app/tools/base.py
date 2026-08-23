"""Base tool contract, metadata definitions, and policy abstractions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """Abstract base class for all tools with explicit capability, policy, and schema contracts."""

    name: str
    description: str
    capability: str = "general"
    read_only: bool = True
    requires_confirmation: bool = False
    timeout_seconds: float = 10.0
    parameters: Dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool with given arguments and return structured results."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Return complete metadata descriptor for discovery, permission, and audit."""
        return {
            "name": self.name,
            "description": self.description,
            "capability": self.capability,
            "read_only": self.read_only,
            "requires_confirmation": self.requires_confirmation,
            "timeout_seconds": self.timeout_seconds,
            "parameters": self.parameters,
        }

    def to_deepgram_function_schema(self) -> Dict[str, Any]:
        """Convert tool definition to Deepgram / Groq function calling schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
