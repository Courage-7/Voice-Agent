"""Tool package.

The registry intentionally lives in :mod:`app.tools.registry`; it used to be
copied into this package initializer, which created two registry singletons.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.tools.registry import ToolRegistry, tool_registry

__all__ = ["ToolRegistry", "tool_registry"]


def __getattr__(name: str):
    """Load registry exports lazily without creating package import cycles."""
    if name in __all__:
        from app.tools.registry import ToolRegistry, tool_registry

        return {"ToolRegistry": ToolRegistry, "tool_registry": tool_registry}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
