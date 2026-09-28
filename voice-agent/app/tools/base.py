"""Base tool contract, metadata definitions, and policy abstractions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Tuple


class BaseTool(ABC):
    """Abstract base class for all tools with explicit capability, policy, and schema contracts."""

    name: str
    description: str
    capability: str = "general"
    read_only: bool = True
    requires_confirmation: bool = False
    timeout_seconds: float = 10.0
    parameters: Dict[str, Any]
    # Provider adapters declare these; the planner and execution engine only
    # reason over capabilities and operations.
    operations: Tuple[str, ...] = ()
    supported_connected_apps: Tuple[str, ...] = ()
    supports_parallel_execution: bool = True

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
            "operations": list(self.operations),
            "requires_connection": bool(self.supported_connected_apps),
            "supports_parallel_execution": self.supports_parallel_execution,
            "parameters": self.parameters,
        }

    def is_available_for(self, connected_apps: Iterable[str]) -> bool:
        """Whether this provider adapter has an eligible connected account.

        The core registry does not need to know provider names: each adapter
        declares its own compatible account slugs.
        """
        if not self.supported_connected_apps:
            return True
        connected = {str(app).upper() for app in connected_apps}
        return bool(connected.intersection(self.supported_connected_apps))

    def to_deepgram_function_schema(self) -> Dict[str, Any]:
        """Convert a server-executed tool to a Deepgram function contract."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            # Deepgram sends client-side calls back over its WebSocket; the
            # backend is the only execution client for this application.
            "client_side": True,
            # Prevent speculative execution of write/destructive operations.
            "defer_until_eot": not self.read_only,
        }

    def to_deepgram_schema(self) -> Dict[str, Any]:
        """Alias for to_deepgram_function_schema."""
        return self.to_deepgram_function_schema()
